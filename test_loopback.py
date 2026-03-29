import numpy as np
import cv2
import binascii
import os
from core.encoder_engine import EncoderEngine
from core.decoder_engine import DecoderEngine
from core.protocol import OpticalProtocol as P

def test_loopback():
    encoder = EncoderEngine()
    decoder = DecoderEngine()
    
    # 1. 获取单帧纯数据容量 (6676 bits)
    capacity = P.get_data_capacity_per_frame()
    print(f"--- 开始协议回路测试 (BlockSize: {P.BLOCK_SIZE}px) ---")
    print(f"当前单帧数据净容量: {capacity} bits")
    
    # 生成随机原始数据 (模拟一个文件的分片)
    raw_payload_bits = np.random.randint(0, 2, capacity).tolist()
    
    # 2. 构造 Header (模拟 EncoderEngine 内部逻辑)
    # SYNC(16) + SEQ(8, 这里设为0) + LEN(16, 这里是全满)
    sync_bits = P.SYNC_PATTERN
    seq_bits = [int(b) for b in format(0, '08b')]
    len_bits = [int(b) for b in format(capacity, '016b')]
    header_bits = sync_bits + seq_bits + len_bits
    
    # 3. 计算全局 CRC (Header + Payload)
    # 必须与 EncoderEngine.generate_all_frames 的逻辑完全一致
    combined_content = header_bits + raw_payload_bits
    content_bytes = encoder._bits_to_bytes(combined_content)
    crc_val = binascii.crc32(content_bytes) & 0xFFFF
    crc_bits = [int(b) for b in format(crc_val, f'0{P.CRC_BITS}b')]
    
    # 拼接最终待绘制的比特流
    full_frame_bits = header_bits + raw_payload_bits + crc_bits
    
    print(f"DEBUG: 原始 Payload 前 16 位: {raw_payload_bits[:16]}")
    
    # 4. 编码渲染
    # 此时背景是 1008x1008
    base_frame = encoder.create_base_frame()
    frame_img = encoder.draw_data(base_frame, full_frame_bits)
    cv2.imwrite("debug_test_frame.png", frame_img)
    print("✅ 编码完成，已保存 debug_test_frame.png")
    
    # 5. 解码识别
    img_gray = cv2.imread("debug_test_frame.png", cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        print("❌ 错误：无法读取生成的测试图片")
        return

    # 调用 decoder 的核心解析逻辑
    # process_frame 内部会自动处理：采样 -> 拆解 -> CRC校验 -> 去重 -> 裁剪
    success, recovered_payload = decoder.process_frame(img_gray)
    
    # 6. 输出对比报告
    print(f"\n--- 协议测试报告 ---")
    
    if success == True:
        print(f"预期数据长度: {len(raw_payload_bits)} bits | 实际还原长度: {len(recovered_payload)} bits")
        
        # 逐位对比内容
        if recovered_payload == raw_payload_bits:
            print("🎉 完美匹配！1008px 矩阵与全局 CRC 校验通过。")
        else:
            diff_idx = next(i for i, (a, b) in enumerate(zip(raw_payload_bits, recovered_payload)) if a != b)
            print(f"❌ 数据内容不匹配！起始错误位置索引: {diff_idx}")
    elif success == "SKIP":
        print("⚠️ 帧被跳过（序号重复）")
    else:
        print("❌ 解析失败：同步码不匹配或 CRC 校验未通过。")

if __name__ == "__main__":
    test_loopback()