#!/usr/bin/env python3
"""
发送端（编码器）
功能：读取二进制文件，编码为图像序列，生成视频

命令行接口：
    python encoder.py in.bin out.mp4 1000
    
参数：
    argv[1]: 输入二进制文件
    argv[2]: 输出视频文件
    argv[3]: 视频最大时长（毫秒）

流程：
    二进制文件 → 比特流 → 分帧(CRC) → 生成图像 → 合成视频
"""

import os
import sys

# 添加当前目录到 Python 路径（确保可以导入 core 和 utils）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shutil
from core.encoder_engine import EncoderEngine
from core.protocol import OpticalProtocol as P
from utils.video_muxer import VideoMuxer


def file_to_bits(file_path):
    """将二进制文件转换为比特列表"""
    with open(file_path, 'rb') as f:
        data = f.read()
    
    bits = []
    for byte in data:
        for i in range(7, -1, -1):  # 高位在前
            bits.append((byte >> i) & 1)
    return bits


def main():
    # 检查参数
    if len(sys.argv) != 4:
        print("用法: python encoder.py <输入文件> <输出视频> <时长限制(ms)>")
        print("示例: python encoder.py in.bin out.mp4 1000")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    try:
        max_duration_ms = int(sys.argv[3])
    except ValueError:
        print(f"❌ 错误：时长限制必须是整数（毫秒）")
        sys.exit(1)
    
    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"❌ 错误：输入文件不存在: {input_file}")
        sys.exit(1)
    
    # 计算最大允许帧数
    fps = P.FPS
    max_frames = int((max_duration_ms / 1000.0) * fps)
    capacity_per_frame = P.get_data_capacity_per_frame()
    max_bits = max_frames * capacity_per_frame
    
    print(f"=" * 50)
    print(f"📤 可见光通信发送端")
    print(f"=" * 50)
    print(f"输入文件: {input_file}")
    print(f"输出视频: {output_file}")
    print(f"时长限制: {max_duration_ms} ms")
    print(f"帧率: {fps} FPS")
    print(f"最大帧数: {max_frames}")
    print(f"每帧容量: {capacity_per_frame} bits")
    print(f"最大数据量: {max_bits} bits ({max_bits // 8} bytes)")
    print(f"=" * 50)
    
    # 1. 读取二进制文件为比特流
    print("\n📖 步骤1: 读取二进制文件...")
    all_bits = file_to_bits(input_file)
    file_size = os.path.getsize(input_file)
    print(f"   文件大小: {file_size} bytes ({len(all_bits)} bits)")
    
    # 检查数据是否超出容量
    if len(all_bits) > max_bits:
        print(f"\n⚠️  警告：数据超出容量限制！")
        print(f"   数据大小: {len(all_bits)} bits")
        print(f"   最大容量: {max_bits} bits")
        print(f"   将截断数据至 {max_bits} bits")
        all_bits = all_bits[:max_bits]
    
    # 2. 编码为图像序列
    print("\n🎨 步骤2: 编码为图像序列...")
    
    # 清理并创建临时目录
    frames_dir = "temp/encoder_frames"
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    
    encoder = EncoderEngine()
    total_frames = (len(all_bits) + capacity_per_frame - 1) // capacity_per_frame
    print(f"   预计帧数: {total_frames}")
    print(f"   预计时长: {total_frames / fps * 1000:.1f} ms")
    
    frame_count = encoder.generate_all_frames(all_bits, frames_dir)
    
    # 检查是否超出帧数限制
    if frame_count > max_frames:
        print(f"\n❌ 错误：生成的帧数({frame_count})超过限制({max_frames})")
        print(f"   请减少数据量或增加时长限制")
        sys.exit(1)
    
    # 3. 合成视频（优先使用FFmpeg无损编码）
    print("\n🎬 步骤3: 合成视频...")
    ffmpeg_used = VideoMuxer.ffmpeg_convert(frames_dir, output_file, fps=fps)
    if not ffmpeg_used:
        print("   已使用 OpenCV 编码完成")
    
    # 4. 验证视频时长
    print("\n🔍 步骤4: 验证视频...")
    import cv2
    cap = cv2.VideoCapture(output_file)
    if cap.isOpened():
        actual_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        actual_duration_ms = (actual_frame_count / actual_fps) * 1000 if actual_fps > 0 else 0
        cap.release()
        
        print(f"   实际帧数: {actual_frame_count}")
        print(f"   实际时长: {actual_duration_ms:.1f} ms")
        
        if actual_duration_ms > max_duration_ms:
            print(f"\n❌ 错误：视频时长({actual_duration_ms:.1f}ms)超过限制({max_duration_ms}ms)")
            sys.exit(1)
    
    # 5. 清理临时文件
    print("\n🧹 步骤5: 清理临时文件...")
    shutil.rmtree(frames_dir, ignore_errors=True)
    
    # 6. 输出统计信息
    print("\n" + "=" * 50)
    print(f"✅ 编码完成!")
    print(f"=" * 50)
    print(f"生成帧数: {frame_count}")
    print(f"视频时长: {frame_count / fps * 1000:.1f} ms")
    print(f"输出文件: {output_file}")
    
    if os.path.exists(output_file):
        video_size = os.path.getsize(output_file)
        print(f"视频大小: {video_size / 1024:.2f} KB")
    
    print(f"=" * 50)


if __name__ == "__main__":
    main()