import cv2
import binascii
import numpy as np
from core.protocol import OpticalProtocol as p

class DecoderEngine:
    def __init__(self):
        self.p = p()
        self.last_seq = -1 
        self.sample_radius = 2 # 针对 10px 格子，2 是理想半径

    def _bits_to_int(self, bits):
        if not bits: return 0
        return int("".join(map(str, bits)), 2)

    def _bits_to_bytes(self, bits):
        byte_arr = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            chunk = bits[i:i+8]
            for bit in chunk:
                byte = (byte << 1) | bit
            if len(chunk) < 8:
                byte <<= (8 - len(chunk))
            byte_arr.append(byte)
        return bytes(byte_arr)

    def _get_robust_bit(self, img, x_c, y_c):
        r = self.sample_radius
        y_min, y_max = max(0, y_c - r), min(img.shape[0], y_c + r + 1)
        x_min, x_max = max(0, x_c - r), min(img.shape[1], x_c + r + 1)
        
        roi = img[y_min:y_max, x_min:x_max]
        if roi.size == 0: return 0
        
        # 中值滤波判定：超过阈值为 1 (白)，否则为 0 (黑)
        median_val = np.median(roi)
        return 1 if median_val > self.p.THRESHOLD else 0

    def frame_to_bits(self, img):
        """
        全量提取非锚点区的比特流
        """
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
        recovered_bits = []
        bs = self.p.BLOCK_SIZE # 10
        offset = bs // 2       # 5

        for r in range(self.p.ROWS):
            for c in range(self.p.COLS):
                # 严格对齐 Protocol 的 8x8 跳过逻辑
                if self.p.is_in_anchor_zone(r, c):
                    continue 
                
                # 因为背景已经是 1000x1000，所以无需再加 OFFSET_X/Y
                x_center = int(c * bs + offset)
                y_center = int(r * bs + offset)
                
                bit = self._get_robust_bit(img, x_center, y_center)
                recovered_bits.append(bit)

        return recovered_bits
    
    def process_frame(self, img):
        """
        适配全局 CRC 逻辑：校验对象为 [Header + Payload]
        """
        received_seq = -1
        all_bits = self.frame_to_bits(img)
        
        # 基础长度检查 (SYNC 16 + SEQ 8 + LEN 16 + CRC 16 = 56)
        if len(all_bits) < 56:
            return False, None, received_seq

        # 1. 拆解 Header
        cursor = 0
        # 同步码 (16位)
        received_sync = all_bits[cursor : cursor + self.p.SYNC_BITS]
        cursor += self.p.SYNC_BITS
        
        # 同步码比对 (如果不匹配直接退出，节省性能)
        if received_sync != self.p.SYNC_PATTERN:
            return False, None, received_seq

        # 帧序号 (8位)
        received_seq = self._bits_to_int(all_bits[cursor : cursor + self.p.SEQ_BITS])
        cursor += self.p.SEQ_BITS
        
        # 有效载荷长度 (16位)
        received_len = self._bits_to_int(all_bits[cursor : cursor + self.p.LEN_BITS])
        cursor += self.p.LEN_BITS
        
        # 2. 提取 Payload 和 CRC
        capacity = self.p.get_data_capacity_per_frame()
        # 这里的 payload 指的是填满整帧的原始部分 (含填充0)
        payload_bits = all_bits[cursor : cursor + capacity]
        
        # CRC 始终位于比特流的最后 16 位
        received_crc_bits = all_bits[-self.p.CRC_BITS:]
        received_crc_val = self._bits_to_int(received_crc_bits)

        # 3. 校验逻辑 (核心修改点：必须包含 Header)
        # 编码端计算逻辑：binascii.crc32(Header + Chunk)
        header_bits = all_bits[:self.p.SYNC_BITS + self.p.SEQ_BITS + self.p.LEN_BITS]
        combined_for_crc = header_bits + payload_bits
        
        calculated_crc = binascii.crc32(self._bits_to_bytes(combined_for_crc)) & 0xFFFF
        
        if calculated_crc != received_crc_val:
            # print(f"❌ CRC 校验失败 | Seq: {received_seq} (收:{received_crc_val:04X} 算:{calculated_crc:04X})")
            return False, None, received_seq
        
        # 4. 序号去重
        if received_seq == self.last_seq:
            return "SKIP", None, received_seq
        
        self.last_seq = received_seq

        # 5. 根据 LEN 字段精确裁剪
        final_payload = payload_bits[:received_len]
        
        print(f"✅ 帧解析成功 | Seq: {received_seq} | Len: {received_len} bits")
        return True, final_payload, received_seq