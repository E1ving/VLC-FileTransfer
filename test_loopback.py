import numpy as np
import cv2
import binascii
from core.encoder_engine import EncoderEngine
from core.decoder_engine import DecoderEngine
from core.protocol import OpticalProtocol as P

def test_loopback():
    encoder = EncoderEngine()
    decoder = DecoderEngine()
    
    # 1. 准备：生成 2864 位纯数据载荷
    payload_bits = np.random.randint(0, 2, 2864).tolist()
    
    # 2. 计算并拼接 CRC (为了模拟真实的编码器行为)
    payload_bytes = encoder._bits_to_bytes(payload_bits)
    crc_val = binascii.crc32(payload_bytes) & 0xFFFF
    crc_bits = [int(b) for b in format(crc_val, '016b')] # 转为 16 个 bit
    
    # 更新为 2880 位
    full_frame_bits = payload_bits + crc_bits # 总共 2880 位
    
    print(f"DEBUG: 原始 Payload 前 16 位: {payload_bits[:16]}")
    print(f"DEBUG: 编码端计算的 Bytes(前2字节): {payload_bytes[:2].hex()}")
    
    # 3. 编码：生成图片
    base_frame = encoder.create_base_frame()
    frame_img = encoder.draw_data(base_frame, full_frame_bits)
    cv2.imwrite("debug_test_frame.png", frame_img)
    
    # 4. 解码：抠出 2880 位
    img_gray = cv2.imread("debug_test_frame.png", cv2.IMREAD_GRAYSCALE)
    recovered_full = decoder.frame_to_bits(img_gray) # 得到 2880 位
    
    # 5. 校验：拆解数据与 CRC
    rec_payload = recovered_full[:2864]
    rec_crc_bits = recovered_full[2864:]
    
    # 计算还原出的数据的 CRC
    rec_payload_bytes = decoder._bits_to_bytes(rec_payload)
    calc_crc = binascii.crc32(rec_payload_bytes) & 0xFFFF
    rec_crc_val = int("".join(map(str, rec_crc_bits)), 2)
    
    print(f"DEBUG: 还原 Payload 前 16 位: {rec_payload[:16]}")
    print(f"DEBUG: 解码端还原的 Bytes(前2字节): {rec_payload_bytes[:2].hex()}")
    
    # 6. 输出结果
    print(f"--- 协议测试报告 ---")
    print(f"有效数据位数: {len(rec_payload)}")
    print(f"编码 CRC: {crc_val:04X} | 解码还原 CRC: {rec_crc_val:04X}")
    
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