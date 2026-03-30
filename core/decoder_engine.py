# core/decoder_engine.py
import cv2
import numpy as np
import binascii
from core.protocol import OpticalProtocol as P

class DecoderEngine:
    def __init__(self):
        self.p = P()

    def _bits_to_bytes(self, bits):
        """将比特流转为字节，用于 CRC 计算"""
        byte_arr = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for bit in bits[i:i+8]:
                byte = (byte << 1) | bit
            byte_arr.append(byte)
        return bytes(byte_arr)

    def frame_to_bits(self, img):
        """核心逻辑：将一张图片还原为比特列表"""
        # 如果图片是彩色的，转为灰度图
        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
        recovered_bits = []
        for r in range(self.p.ROWS):
            for c in range(self.p.COLS):

                if self.p.is_in_anchor_zone(r, c):
                    continue # 跳过定位区，保证和编码端顺序一致
                
                # 2. 计算格子的中心采样点坐标
                # 采样中心点最稳健，可以避开格子边缘的模糊
                x_center = self.p.OFFSET_X + c * self.p.BLOCK_SIZE + (self.p.BLOCK_SIZE // 2)
                y_center = self.p.OFFSET_Y + r * self.p.BLOCK_SIZE + (self.p.BLOCK_SIZE // 2)
                
                # 3. 读取像素值并判定
                pixel_value = img[y_center, x_center]
                bit = 1 if pixel_value > self.p.THRESHOLD else 0
                recovered_bits.append(bit)

        return recovered_bits
    
    def process_frame(self, img):
        """
        核心逻辑：输入一张图，输出 (这一帧的数据比特, 这一帧的有效性列表)
        """
        capacity = self.p.get_data_capacity_per_frame()
        crc_bits = self.p.CRC_BITS
        total_bits = capacity + crc_bits
        
        # 1. 物理采样：获取所有比特 (数据 + CRC)
        all_sampled_bits = self.frame_to_bits(img)
        
        # 如果采样位数不足，返回空
        if len(all_sampled_bits) < total_bits:
            return [], [0] * capacity
        
        # 2. 分离数据和 CRC
        data_bits = all_sampled_bits[:capacity]
        received_crc_bits = all_sampled_bits[capacity:capacity + crc_bits]
        
        # 3. 执行 CRC 校验
        data_bytes = self._bits_to_bytes(data_bits)
        calculated_crc = binascii.crc32(data_bytes) & 0xFFFF
        # 将收到的 16 位比特转回整数进行对比
        received_crc_val = int("".join(map(str, received_crc_bits)), 2)
        is_valid = (calculated_crc == received_crc_val)
        
        # 4. 生成这一帧的 vout 状态
        # 根据要求：每一位数据对应一个状态字节。正确为 1，错误为 0
        status = 1 if is_valid else 0
        frame_vout = [status] * len(data_bits)
        
        return data_bits, frame_vout
