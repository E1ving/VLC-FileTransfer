import cv2
import numpy as np
import os
import binascii
from core.protocol import OpticalProtocol as p

class EncoderEngine:
    def __init__(self):
        self.p = p()

    def _fill_block(self, canvas, r, c, color):
        """填充单个 12x12 的格子"""
        bs = p.BLOCK_SIZE  
        canvas[r*bs : (r+1)*bs, c*bs : (c+1)*bs] = color

    def create_base_frame(self):
        """
        创建 1008x1008 基础帧
        锚点 7x7 紧贴物理边角，内侧留 1 格白边
        """
        img = np.ones((self.p.SCREEN_H, self.p.SCREEN_W), dtype=np.uint8) * 255
        res = self.p.ANCHOR_RESERVE  # 8

        for r in range(self.p.ROWS):
            for c in range(self.p.COLS):
                if self.p.is_in_anchor_zone(r, c):
                    # 获取局部坐标 (0-7)
                    lr = r if r < res else (r - (self.p.ROWS - res))
                    lc = c if c < res else (c - (self.p.COLS - res))
                    
                    is_right = c >= (self.p.COLS - res)
                    is_bottom = r >= (self.p.ROWS - res)

                    # 计算锚点在该 8x8 区域内的起始偏移
                    # 左/上贴边 -> offset=0; 右/下贴边 -> offset=1 (因为 8-7=1)
                    off_r = 1 if is_bottom else 0
                    off_c = 1 if is_right else 0

                    # 检查是否落在 7x7 锚点绘制区内
                    dr, dc = lr - off_r, lc - off_c
                    
                    if 0 <= dr < 7 and 0 <= dc < 7:
                        # 7x7 核心逻辑
                        dist = max(abs(dr - 3), abs(dc - 3))
                        color = 0 if dist != 2 else 255
                        self._fill_block(img, r, c, color)
                    else:
                        # 隔离带（白边）
                        self._fill_block(img, r, c, 255)
        return img

    def draw_data(self, img, full_frame_bits):
        """将比特流按行顺序填入非锚点区"""
        bit_idx = 0
        for r in range(p.ROWS):
            for c in range(p.COLS):
                # 严格对齐 Protocol 的 8x8 跳过逻辑
                if p.is_in_anchor_zone(r, c):
                    continue
                
                if bit_idx < len(full_frame_bits):
                    color = 255 if full_frame_bits[bit_idx] == 1 else 0
                    self._fill_block(img, r, c, color)
                    bit_idx += 1
        return img

    def _int_to_bits(self, value, bit_count):
        return [int(b) for b in format(value, f'0{bit_count}b')]

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

    def generate_all_frames(self, all_bits, output_dir="data/frames"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        capacity = p.get_data_capacity_per_frame()
        frame_count = 0
        
        for i in range(0, len(all_bits), capacity):
            chunk = all_bits[i : i + capacity]
            actual_len = len(chunk)
            
            # 1. 物理填充（补齐到 capacity 长度）
            if len(chunk) < capacity:
                chunk += [0] * (capacity - len(chunk))
            
            # 2. 构造 Header (SYNC + SEQ + LEN)
            header_bits = (p.SYNC_PATTERN + 
                           self._int_to_bits(frame_count % 256, p.SEQ_BITS) + 
                           self._int_to_bits(actual_len, p.LEN_BITS))
            
            # 3. 计算 CRC - 关键修改：此时 combined_content 长度必须固定
            combined_content = header_bits + chunk
            # 确保转换字节时是 8 位对齐的，防止位偏移
            data_to_crc = self._bits_to_bytes(combined_content)
            crc_val = binascii.crc32(data_to_crc) & 0xFFFF
            crc_bits = self._int_to_bits(crc_val, p.CRC_BITS)
            
            # 4. 组装全帧
            full_frame_bits = header_bits + chunk + crc_bits

            # 5. 渲染保存
            base_img = self.create_base_frame()
            final_frame = self.draw_data(base_img, full_frame_bits)
            
            cv2.imwrite(f"{output_dir}/frame_{frame_count:04d}.png", final_frame)
            frame_count += 1