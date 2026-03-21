import cv2
import numpy as np
import os
import binascii
from core.protocol import OpticalProtocol as p

class EncoderEngine:
    def __init__(self):
        self.p = p()

    def create_base_frame(self):
        """
        改良版：在 8x8 的逻辑区域内绘制稍微缩小的锚点
        逻辑：背景依旧是黑色的隔离带，中心绘制 120x120 的嵌套锚点（原为 144x144）
        """
        img = np.zeros((p.SCREEN_H, p.SCREEN_W), dtype=np.uint8)
        
        # 逻辑上的锚点尺寸 (8格 * 18px = 144px)
        logical_anchor_size = p.ANCHOR_SIZE 
        # 实际绘制的锚点尺寸 (缩减一些，预留出四周各 12px 的黑色隔离带)
        draw_size = p.DRAW_ANCHOR_SIZE 
        padding = (logical_anchor_size - draw_size) // 2
        
        # 内部细节比例调整
        border_width = 15 # 略微减细
        
        # 逻辑上的四个角位置
        anchors_logic = [
            (p.OFFSET_X, p.OFFSET_Y), 
            (p.OFFSET_X + p.DATA_AREA_SIZE - logical_anchor_size, p.OFFSET_Y),
            (p.OFFSET_X + p.DATA_AREA_SIZE - logical_anchor_size, p.OFFSET_Y + p.DATA_AREA_SIZE - logical_anchor_size),
            (p.OFFSET_X, p.OFFSET_Y + p.DATA_AREA_SIZE - logical_anchor_size)
        ]
        
        for i, (lx, ly) in enumerate(anchors_logic):
            # 实际绘制坐标（逻辑坐标 + 偏移量）
            x, y = lx + padding, ly + padding
            
            # 1. 绘制实心白块 (120x120)
            cv2.rectangle(img, (x, y), (x + draw_size, y + draw_size), 255, -1)
            
            # 2. 绘制内部黑框
            cv2.rectangle(img, (x + border_width, y + border_width), 
                          (x + draw_size - border_width, y + draw_size - border_width), 0, border_width)
            
            # 3. 绘制中心孔
            # 右下角(i=2)的孔设为不同大小，方便辅助判定方向
            hole_size = 50 if i != 2 else 24 
            hole_off = (draw_size - hole_size) // 2
            cv2.rectangle(img, (x + hole_off, y + hole_off), 
                          (x + hole_off + hole_size, y + hole_off + hole_size), 0, -1)
            
        return img

    def _int_to_bits(self, value, bit_count):
        """将整数转为指定长度的比特列表"""
        return [int(b) for b in format(value, f'0{bit_count}b')]

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
    
    def draw_data(self, img, full_frame_bits):
        """将完整的帧比特流（含Header）绘制到图像"""
        bit_idx = 0
        for r in range(p.ROWS):
            for c in range(p.COLS):
                if p.is_in_anchor_zone(r, c):
                    continue
                
                if bit_idx < len(full_frame_bits):
                    x1, y1, x2, y2 = p.get_block_rect(r, c)
                    # 绘制数据块
                    color = 255 if full_frame_bits[bit_idx] == 1 else 0
                    img[y1:y2, x1:x2] = color
                    bit_idx += 1
        return img

    def generate_all_frames(self, all_bits, output_dir="data/frames"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        capacity = p.get_data_capacity_per_frame()
        frame_count = 0
        
        # 逐帧封装
        for i in range(0, len(all_bits), capacity):
            chunk = all_bits[i : i + capacity]
            actual_len = len(chunk)
            
            # 1. 填充最后一帧
            if len(chunk) < capacity:
                chunk += [0] * (capacity - len(chunk))
            
            # 2. 构造 Header (同步码 + 帧序号 + 长度)
            sync_bits = p.SYNC_PATTERN
            seq_bits = self._int_to_bits(frame_count % 256, p.SEQ_BITS)
            len_bits = self._int_to_bits(actual_len, p.LEN_BITS)
            
            header_bits = sync_bits + seq_bits + len_bits
            
            # 3. 计算 CRC (针对 Header + Payload)
            # 只有对整个序列校验才最保险
            combined_for_crc = header_bits + chunk
            chunk_bytes = self._bits_to_bytes(combined_for_crc)
            crc_val = binascii.crc32(chunk_bytes) & 0xFFFF
            crc_bits = self._int_to_bits(crc_val, p.CRC_BITS)
            
            # 4. 组装最终绘制序列
            # 顺序：[SYNC][SEQ][LEN] + [DATA] + [CRC]
            full_frame_bits = header_bits + chunk + crc_bits

            # 5. 渲染保存
            base_img = self.create_base_frame()
            final_frame = self.draw_data(base_img, full_frame_bits)
            
            cv2.imwrite(f"{output_dir}/frame_{frame_count:04d}.png", final_frame)
            frame_count += 1
            
        print(f"✅ 已成功封装 {frame_count} 帧 (Header已嵌入)")
