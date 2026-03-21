# core/decoder_engine.py
import cv2
import binascii
import numpy as np
from core.protocol import OpticalProtocol as p

class DecoderEngine:
    def __init__(self):
        self.p = p()
        self.last_seq = -1 # 用于记录上一帧序号，辅助去重
        # 采样半径：2 表示检查中心点周围 5x5 的像素区域
        self.sample_radius = 2

    def _bits_to_int(self, bits):
        """工具函数：比特列表转整数"""
        if not bits: return 0
        return int("".join(map(str, bits)), 2)

    def _bits_to_bytes(self, bits):
        """将比特流转为字节，用于 CRC 计算"""
        byte_arr = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            # 取 8 位组成一个字节，不足 8 位后面补 0（逻辑对齐）
            chunk = bits[i:i+8]
            for bit in chunk:
                byte = (byte << 1) | bit
            if len(chunk) < 8:
                byte <<= (8 - len(chunk))
            byte_arr.append(byte)
        return bytes(byte_arr)

    def _get_robust_bit(self, img, x_c, y_c):
        """
        核心采样函数：通过中值滤波判定比特位
        """
        r = self.sample_radius
        # 边界保护
        y_min, y_max = max(0, y_c - r), min(img.shape[0], y_c + r + 1)
        x_min, x_max = max(0, x_c - r), min(img.shape[1], x_c + r + 1)
        
        roi = img[y_min:y_max, x_min:x_max]
        
        if roi.size == 0:
            return 0
            
        # 取中值：如果区域内一半以上像素亮，则判为 1
        median_val = np.median(roi)
        return 1 if median_val > self.p.THRESHOLD else 0

    def frame_to_bits(self, img):
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
        recovered_bits = []
        block_size = self.p.BLOCK_SIZE
        
        # --- 核心对齐逻辑 ---
        # 1. VisionCorrector 把锚点中心映射到了 margin 坐标。
        # 2. 协议规定，左上锚点的中心逻辑位置是 (1.5 * block_size)。
        # 3. 所以，逻辑上的 (0,0) 数据块中心，在物理图像上的坐标应该是：
        #    物理坐标 = margin - 锚点中心逻辑偏移 + 0.5个块的中心偏移
        
        margin = block_size  # 必须与 VisionCorrector 里的 margin 一致
        # 这里的 1.5 是关键，如果红点还偏右，就把它改大（如 1.6）；如果偏左，就改小
        logic_anchor_center = 1.5 * block_size
        
        # 这个 origin_pos 就是数据网格 (0,0) 块的左上角在图中的物理位置
        origin_pos = margin - logic_anchor_center + (block_size // 2)

        for r in range(self.p.ROWS):
            for c in range(self.p.COLS):
                if self.p.is_in_anchor_zone(r, c):
                    continue 
                
                # 计算采样中心：物理原点 + 当前块偏移 + 块内中心偏置
                x_center = int(origin_pos + (c * block_size) + (block_size // 2))
                y_center = int(origin_pos + (r * block_size) + (block_size // 2))
                
                # 越界检查
                if 0 <= x_center < img.shape[1] and 0 <= y_center < img.shape[0]:
                    bit = self._get_robust_bit(img, x_center, y_center)
                else:
                    bit = 0
                recovered_bits.append(bit)

        return recovered_bits
    
    def process_frame(self, img):
        """
        升级版逻辑：[Header(40位)] + [Data(2824位)] + [CRC(16位)]
        返回: (is_valid, payload_bits)
        """
        # 1. 物理采样获取全量比特 (共 2880 位)
        all_bits = self.frame_to_bits(img)
        
        # 2. 拆解 Header (根据协议定义)
        offset = 0
        # 同步码 (16位)
        received_sync = all_bits[offset : offset + p.SYNC_BITS]
        offset += p.SYNC_BITS
        # 帧序号 (8位)
        received_seq = self._bits_to_int(all_bits[offset : offset + p.SEQ_BITS])
        offset += p.SEQ_BITS
        # 有效载荷长度 (16位)
        received_len = self._bits_to_int(all_bits[offset : offset + p.LEN_BITS])
        offset += p.LEN_BITS
        
        # 3. 拆解 Payload 和 CRC
        # 注意：这里先取全额 payload 位，之后根据 received_len 裁剪
        payload_bits = all_bits[offset : offset + p.get_data_capacity_per_frame()]
        received_crc_val = self._bits_to_int(all_bits[-p.CRC_BITS:])

        # --- 校验逻辑 ---
        
        # A. 同步码比对
        if received_sync != p.SYNC_PATTERN:
            # 同步失败通常意味着图像定位不准或拍到了干扰
            return False, None

        # B. 全帧 CRC 校验 (针对 Header + Payload 整体校验)
        # 注意：计算 CRC 时必须与编码端的输入完全一致
        header_bits = all_bits[:p.SYNC_BITS + p.SEQ_BITS + p.LEN_BITS]
        full_content_bits = header_bits + payload_bits
        
        calculated_crc = binascii.crc32(self._bits_to_bytes(full_content_bits)) & 0xFFFF
        
        if calculated_crc != received_crc_val:
            print(f"❌ CRC 校验失败 | Seq: {received_seq}")
            return False, None

        # C. 序号去重逻辑
        if self.last_seq == -1:
            # 初始化时，接受任意序号
            pass
        elif received_seq == self.last_seq:
            # 这是一个合法的帧，但它是重复的
            return "SKIP", None
        
        self.last_seq = received_seq

        # D. 根据 LEN 字段精确裁剪数据
        # 这样最后一帧多余的填充 0 就会被自动剔除
        final_payload = payload_bits[:received_len]
        
        print(f"✅ 帧同步成功 | Seq: {received_seq} | Len: {received_len}")
        return True, final_payload