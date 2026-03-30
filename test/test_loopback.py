import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
import binascii
from core.encoder_engine import EncoderEngine
from core.decoder_engine import DecoderEngine
from core.protocol import OpticalProtocol as P

def test_loopback():
    encoder = EncoderEngine()
    decoder = DecoderEngine()
    
    # 1. 准备：生成数据载荷（使用协议定义的容量）
    capacity = P.get_data_capacity_per_frame()
    crc_bits = P.CRC_BITS
    total_bits = capacity + crc_bits
    
    payload_bits = np.random.randint(0, 2, capacity).tolist()
    
    # 2. 计算并拼接 CRC (为了模拟真实的编码器行为)
    payload_bytes = encoder._bits_to_bytes(payload_bits)
    crc_val = binascii.crc32(payload_bytes) & 0xFFFF
    crc_bits_list = [int(b) for b in format(crc_val, '016b')] # 转为 16 个 bit
    
    full_frame_bits = payload_bits + crc_bits_list # 总共 capacity + 16 位
    
    # 3. 编码：生成图片
    base_frame = encoder.create_base_frame()
    frame_img = encoder.draw_data(base_frame, full_frame_bits)
    cv2.imwrite("debug_test_frame.png", frame_img)
    
    # 4. 解码：抠出比特
    img_gray = cv2.imread("debug_test_frame.png", cv2.IMREAD_GRAYSCALE)
    recovered_full = decoder.frame_to_bits(img_gray) # 得到所有比特
    
    # 5. 校验：拆解数据与 CRC
    rec_payload = recovered_full[:capacity]
    rec_crc_bits = recovered_full[capacity:capacity + crc_bits]
    
    # 计算还原出的数据的 CRC
    rec_payload_bytes = decoder._bits_to_bytes(rec_payload)
    calc_crc = binascii.crc32(rec_payload_bytes) & 0xFFFF
    rec_crc_val = int("".join(map(str, rec_crc_bits)), 2)
    
    # 6. 输出结果
    print(f"--- 协议测试报告 ---")
    print(f"协议参数:")
    print(f"  每帧数据容量: {capacity} bits")
    print(f"  CRC 位数: {crc_bits} bits")
    print(f"  总位数: {total_bits} bits")
    print(f"测试结果:")
    print(f"  有效数据位数: {len(rec_payload)}")
    print(f"  编码 CRC: {crc_val:04X} | 解码还原 CRC: {rec_crc_val:04X}")
    
    # 最终对比
    payload_match = (rec_payload == payload_bits)
    crc_match = (calc_crc == rec_crc_val)
    
    if payload_match and crc_match:
        print("🎉 完美匹配！数据与校验位均通过测试。")
    else:
        print(f"❌ 测试失败！")
        if not payload_match: print("   - 数据比特不匹配")
        if not crc_match: print(f"   - CRC 校验失败 (计算值: {calc_crc:04X}, 收到值: {rec_crc_val:04X})")

if __name__ == "__main__":
    test_loopback()