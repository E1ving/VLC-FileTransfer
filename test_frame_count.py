import math
import os

# 模拟帧生成和视频合成过程

def test_frame_count():
    # 模拟参数
    bytes_per_frame = 843  # 6744 bits / 8
    full_data_size = 10000  # 10KB
    capacity = 6744  # 每帧数据容量（bits）
    
    # 计算总帧数
    total_frames_needed = math.ceil(full_data_size / bytes_per_frame)
    print(f"计算的总帧数: {total_frames_needed}")
    
    # 模拟帧生成过程
    all_bits = [0] * (full_data_size * 8)  # 10KB 数据
    generated_frames = 0
    for i in range(0, len(all_bits), capacity):
        generated_frames += 1
    print(f"模拟生成的帧数量: {generated_frames}")
    
    # 验证两者是否一致
    if generated_frames == total_frames_needed:
        print("✅ 帧生成数量与计算的总帧数一致")
    else:
        print("❌ 帧生成数量与计算的总帧数不一致")

if __name__ == "__main__":
    test_frame_count()
