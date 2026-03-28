import cv2
import numpy as np
import os
import binascii
from core.protocol import OpticalProtocol as p

class EncoderEngine:
    def __init__(self):
        self.p = p()
        # 预存基础帧，避免每帧都重新计算背景，极大提升编码速度
        self.base_img_cache = self.create_base_frame()

    def _fill_block(self, canvas, r, c, color):
        """填充单个 12x12 的格子"""
        bs = p.BLOCK_SIZE  
        canvas[r*bs : (r+1)*bs, c*bs : (c+1)*bs] = color

    def create_base_frame(self):
        """创建包含 7x7 锚点的 1008x1008 基础背景帧"""
        img = np.ones((self.p.SCREEN_H, self.p.SCREEN_W), dtype=np.uint8) * 255
        res = self.p.ANCHOR_RESERVE 

        for r in range(self.p.ROWS):
            for c in range(self.p.COLS):
                if self.p.is_in_anchor_zone(r, c):
                    lr = r if r < res else (r - (self.p.ROWS - res))
                    lc = c if c < res else (c - (self.p.COLS - res))
                    
                    off_r = 1 if r >= (self.p.ROWS - res) else 0
                    off_c = 1 if c >= (self.p.COLS - res) else 0

                    dr, dc = lr - off_r, lc - off_c
                    if 0 <= dr < 7 and 0 <= dc < 7:
                        dist = max(abs(dr - 3), abs(dc - 3))
                        color = 0 if dist != 2 else 255
                        self._fill_block(img, r, c, color)
                    else:
                        self._fill_block(img, r, c, 255)
        return img

    def draw_data(self, img, full_frame_bits):
        """将比特流按行顺序填入非锚点区"""
        bit_idx = 0
        # 直接在传入的图像副本上操作
        for r in range(p.ROWS):
            for c in range(p.COLS):
                if p.is_in_anchor_zone(r, c):
                    continue
                
                if bit_idx < len(full_frame_bits):
                    color = 255 if full_frame_bits[bit_idx] == 1 else 0
                    self._fill_block(img, r, c, color)
                    bit_idx += 1
        return img

    def _int_to_bits(self, value, bit_count):
        """将整数转为固定长度的比特列表 (大端)"""
        return [int(b) for b in format(value, f'0{bit_count}b')]

    def _bits_to_bytes(self, bits):
        """高效比特流转字节，用于 CRC 计算"""
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

    # --- 新增：单帧生成接口 ---
    def generate_single_frame(self, chunk_bits, seq, save_path):
        """
        处理单帧的封装与渲染
        :param chunk_bits: 当前帧的数据载荷 (list)
        :param seq: 当前帧序号 (0-255)
        :param save_path: 图片保存路径
        """
        capacity = p.get_data_capacity_per_frame()
        actual_len = len(chunk_bits)

        # 1. 物理填充（补齐到 capacity 长度）
        if len(chunk_bits) < capacity:
            chunk_bits += [0] * (capacity - len(chunk_bits))

        # 2. 构造 Header (SYNC + SEQ + LEN)
        header_bits = (p.SYNC_PATTERN + 
                       self._int_to_bits(seq, p.SEQ_BITS) + 
                       self._int_to_bits(actual_len, p.LEN_BITS))

        # 3. 计算 CRC
        combined_content = header_bits + chunk_bits
        data_to_crc = self._bits_to_bytes(combined_content)
        crc_val = binascii.crc32(data_to_crc) & 0xFFFF
        crc_bits = self._int_to_bits(crc_val, p.CRC_BITS)

        # 4. 组装全帧
        full_frame_bits = header_bits + chunk_bits + crc_bits

        # 5. 渲染保存（使用缓存的基础帧副本）
        frame_canvas = self.base_img_cache.copy()
        final_frame = self.draw_data(frame_canvas, full_frame_bits)
        
        cv2.imwrite(save_path, final_frame)

    # 为了兼容旧版代码，保留此方法但内部调用新接口
    def generate_all_frames(self, all_bits, output_dir="data/frames"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        capacity = p.get_data_capacity_per_frame()
        frame_count = 0
        for i in range(0, len(all_bits), capacity):
            chunk = all_bits[i : i + capacity]
            save_path = f"{output_dir}/frame_{frame_count:05d}.png"
            self.generate_single_frame(chunk, frame_count % 256, save_path)
            frame_count += 1