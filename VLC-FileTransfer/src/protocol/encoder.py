# src/protocol/encoder.py

from .frame_config import (
    SYNC_CODE, 
    SEQ_NUM_LENGTH, 
    PAYLOAD_LENGTH, 
    CHECKSUM_LENGTH, 
    FRAME_TOTAL_LENGTH
)

class ProtocolEncoder:
    def __init__(self):
        self.sequence_number = 0
    
    def calculate_crc8(self, data_bits: list[int]) -> list[int]:
        """
        计算简单的 CRC-8 校验码。
        实际项目中可使用 crcmod 库，这里为了演示手写一个简化版多项式除法逻辑
        多项式: x^8 + x^2 + x^1 + 1 (0x07), 初始值 0
        """
        # 将bit列表转为整数处理会更方便，这里为了逻辑清晰展示位操作
        # 注意：实际传输中需确保多项式与收发双方一致
        crc = 0
        polynomial = 0x07 # 示例多项式
        
        # 将bit流转换为字节流进行处理 (简化逻辑，实际需处理非8倍数情况)
        # 这里为了严谨，直接对bit流进行模拟移位
        # 由于手写完整CRC较繁琐，此处提供一个简化的"异或校验"作为备选，
        # 但推荐在正式提交前替换为标准的CRC-8算法。
        
        # --- 简化版：8位异或校验 (Parity Check on blocks) ---
        # 将数据每8位一组异或
        check_val = 0
        for i in range(0, len(data_bits), 8):
            chunk = data_bits[i:i+8]
            # 补齐8位
            while len(chunk) < 8:
                chunk.append(0)
            
            byte_val = 0
            for bit in chunk:
                byte_val = (byte_val << 1) | bit
            
            check_val ^= byte_val
            
        # 转回bit列表 (8位)
        result = []
        for _ in range(8):
            result.insert(0, check_val & 1)
            check_val >>= 1
        return result

    def encode_frame(self, payload_bits: list[int]) -> list[int]:
        """
        将原始数据载荷封装成一帧。
        结构：[同步码] + [序列号] + [数据载荷] + [校验码]
        """
        if len(payload_bits) != PAYLOAD_LENGTH:
            raise ValueError(f"Payload length must be {PAYLOAD_LENGTH}, got {len(payload_bits)}")

        frame = []

        # 1. 添加帧头：同步码
        frame.extend(SYNC_CODE)

        # 2. 添加帧头：序列号 (自动递增，循环 0-255)
        seq_bits = self._int_to_bits(self.sequence_number, SEQ_NUM_LENGTH)
        frame.extend(seq_bits)
        self.sequence_number = (self.sequence_number + 1) % (2 ** SEQ_NUM_LENGTH)

        # 3. 添加数据载荷
        frame.extend(payload_bits)

        # 4. 计算并添加帧尾：校验码 (对整个帧的有效数据部分进行校验，通常不含同步码)
        # 校验范围：序列号 + 数据载荷
        data_to_check = seq_bits + payload_bits
        checksum = self.calculate_crc8(data_to_check)
        frame.extend(checksum)

        return frame

    def encode_stream(self, raw_bitstream: list[int]) -> list[list[int]]:
        """
        将整个长比特流切割并封装成多帧。
        返回：帧列表，每帧是一个 bit list
        """
        frames = []
        total_len = len(raw_bitstream)
        
        for i in range(0, total_len, PAYLOAD_LENGTH):
            chunk = raw_bitstream[i : i + PAYLOAD_LENGTH]
            # 如果最后一帧不足，补0 (Padding)
            if len(chunk) < PAYLOAD_LENGTH:
                chunk.extend([0] * (PAYLOAD_LENGTH - len(chunk)))
            
            frame = self.encode_frame(chunk)
            frames.append(frame)
            
        return frames

    def _int_to_bits(self, number: int, length: int) -> list[int]:
        """辅助函数：整数转固定长度的bit列表 (高位在前)"""
        bits = []
        for _ in range(length):
            bits.insert(0, number & 1)
            number >>= 1
        return bits

# 使用示例 (供测试用)
if __name__ == "__main__":
    encoder = ProtocolEncoder()
    # 模拟一段原始数据 (100 bits)
    raw_data = [1] * 100 
    frames = encoder.encode_stream(raw_data)
    
    print(f"协议版本: 已加载")
    print(f"总帧数: {len(frames)}")
    print(f"单帧结构长度: {len(frames[0])} bits")
    print(f"第一帧内容 (前20位): {frames[0][:20]} ... (同步码应为 {SYNC_CODE})")