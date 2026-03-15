import cv2
import numpy as np
import os
import binascii
from core.protocol import OpticalProtocol as P

class EncoderEngine:
    def __init__(self):
        self.p = P()

    def create_base_frame(self):
        """升级版：绘制双环嵌套锚点"""
        img = np.zeros((self.p.SCREEN_H, self.p.SCREEN_W), dtype=np.uint8)
        
        # 锚点定义
        anchor_size = self.p.ANCHOR_SIZE
        border_width = 8 # 边框粗细
        
        anchors = [
            (self.p.OFFSET_X, self.p.OFFSET_Y), 
            (self.p.OFFSET_X + 1008 - anchor_size, self.p.OFFSET_Y),
            (self.p.OFFSET_X + 1008 - anchor_size, self.p.OFFSET_Y + 1008 - anchor_size),
            (self.p.OFFSET_X, self.p.OFFSET_Y + 1008 - anchor_size)
        ]
        
        for i, (x, y) in enumerate(anchors):
            # 1. 绘制底色白块
            cv2.rectangle(img, (x, y), (x + anchor_size, y + anchor_size), 255, -1)
            # 2. 绘制黑色边框（在内部，增加对比度）
            hole_size = 60 if i != 2 else 30 # 中心孔大小
            cv2.rectangle(img, (x + border_width, y + border_width), 
                          (x + anchor_size - border_width, y + anchor_size - border_width), 0, border_width)
            # 3. 绘制中心孔（挖空，提供识别特征点）
            hole_off = (anchor_size - hole_size) // 2
            cv2.rectangle(img, (x + hole_off, y + hole_off), 
                          (x + hole_off + hole_size, y + hole_off + hole_size), 0, -1)
            
        return img

    def _bits_to_bytes(self, bits):
        """工具函数：比特流转字节，计算校验用"""
        byte_arr = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for bit in bits[i:i+8]:
                byte = (byte << 1) | bit
            byte_arr.append(byte)
        return bytes(byte_arr)

    def draw_data(self, img, data_with_crc):
        """绘制数据到图片上，跳过定位块区域"""
        bit_idx = 0
        for r in range(self.p.ROWS):
            for c in range(self.p.COLS):
                if self.p.is_in_anchor_zone(r, c):
                    continue
                
                if bit_idx < len(data_with_crc):
                    x1, y1, x2, y2 = self.p.get_block_rect(r, c)
                    img[y1:y2, x1:x2] = 255 if data_with_crc[bit_idx] == 1 else 0
                    bit_idx += 1
        return img

    def generate_all_frames(self, all_bits, output_dir="data/frames"):
        """将总比特流切片并生成序列图"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        capacity = self.p.get_data_capacity_per_frame()
        
        frame_count = 0
        # 按单帧容量切片
        for i in range(0, len(all_bits), capacity):
            chunk = all_bits[i : i + capacity]
            # 补齐最后一帧
            if len(chunk) < capacity:
                break
            
            # 计算 CRC (针对这 2864 位)
            chunk_bytes = self._bits_to_bytes(chunk)
            crc_val = binascii.crc32(chunk_bytes) & 0xFFFF
            crc_bits = [int(b) for b in format(crc_val, '016b')]
            
            # 组合成待绘制的完整序列 (2864 + 16 = 2880 bits)
            data_to_draw = chunk + crc_bits

            # 生成并保存
            base_img = self.create_base_frame()
            final_frame = self.draw_data(base_img, data_to_draw)
            
            cv2.imwrite(f"{output_dir}/frame_{frame_count:04d}.png", final_frame)
            frame_count += 1
            
        print(f"✅ 已生成 {frame_count} 帧图片至 {output_dir}")
