#!/usr/bin/env python3
"""
接收端（解码器）
功能：读取视频，解码为图像序列，还原二进制文件

命令行接口：
    python decoder.py recorded.mp4 out.bin vout.bin
    
参数：
    argv[1]: 输入视频文件（手机拍摄）
    argv[2]: 输出二进制文件
    argv[3]: 有效性标记输出文件

流程：
    视频 → 拆解为帧 → 逐帧解码(CRC校验) → 合并比特流 → 二进制文件
"""

import os
import sys

# 添加当前目录到 Python 路径（确保可以导入 core 和 utils）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shutil
import cv2
from core.decoder_engine import DecoderEngine
from core.protocol import OpticalProtocol as P
from utils.video_muxer import VideoMuxer


def bits_to_file(bits, file_path):
    """将比特列表保存为二进制文件"""
    byte_arr = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i:i+8]
        # 补齐8位
        while len(chunk) < 8:
            chunk.append(0)
        
        byte_val = 0
        for bit in chunk:
            byte_val = (byte_val << 1) | bit
        byte_arr.append(byte_val)
    
    with open(file_path, 'wb') as f:
        f.write(byte_arr)


def save_vout_bits(vout_list, file_path):
    """
    保存有效性标记到文件
    格式：每字节表示 out.bin 中对应字节的8位掩码
    - 位为1表示该位正确
    - 位为0表示该位错误
    """
    byte_arr = bytearray()
    for i in range(0, len(vout_list), 8):
        chunk = vout_list[i:i+8]
        # 补齐8位
        while len(chunk) < 8:
            chunk.append(0)
        
        # 将8个bit打包成一个字节（高位在前）
        byte_val = 0
        for bit in chunk:
            byte_val = (byte_val << 1) | (bit & 1)
        byte_arr.append(byte_val)
    
    with open(file_path, 'wb') as f:
        f.write(byte_arr)


def main():
    # 检查参数
    if len(sys.argv) != 4:
        print("用法: python decoder.py <输入视频> <输出文件> <有效性标记文件>")
        print("示例: python decoder.py recorded.mp4 out.bin vout.bin")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    vout_file = sys.argv[3]
    
    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"❌ 错误：输入视频不存在: {input_file}")
        sys.exit(1)
    
    print(f"=" * 50)
    print(f"📥 可见光通信接收端")
    print(f"=" * 50)
    print(f"输入视频: {input_file}")
    print(f"输出文件: {output_file}")
    print(f"有效性标记: {vout_file}")
    print(f"=" * 50)
    
    # 1. 拆解视频为帧
    print("\n🎥 步骤1: 拆解视频...")
    frames_dir = "temp/decoder_frames"
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    
    VideoMuxer.video_to_frames(input_file, frames_dir)
    
    # 获取所有帧文件
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    if not frame_files:
        print("❌ 错误：未能提取到任何帧")
        sys.exit(1)
    
    print(f"   提取到 {len(frame_files)} 帧")
    
    # 2. 逐帧解码
    print("\n🔍 步骤2: 逐帧解码...")
    decoder = DecoderEngine()
    
    all_data_bits = []
    all_vout = []
    valid_frame_count = 0
    invalid_frame_count = 0
    
    for i, frame_file in enumerate(frame_files):
        frame_path = os.path.join(frames_dir, frame_file)
        img = cv2.imread(frame_path, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
            print(f"   ⚠️  警告：无法读取帧 {frame_file}")
            continue
        
        # 解码这一帧
        data_bits, frame_vout = decoder.process_frame(img)
        
        if not data_bits:
            print(f"   ⚠️  警告：帧 {frame_file} 解码失败")
            continue
        
        # 检查CRC有效性
        is_valid = frame_vout[0] == 1 if frame_vout else False
        if is_valid:
            valid_frame_count += 1
        else:
            invalid_frame_count += 1
        
        all_data_bits.extend(data_bits)
        all_vout.extend(frame_vout)
        
        # 每10帧显示一次进度
        if (i + 1) % 10 == 0 or i == len(frame_files) - 1:
            print(f"   进度: {i + 1}/{len(frame_files)} 帧 ({valid_frame_count} 有效, {invalid_frame_count} 无效)")
    
    # 3. 保存结果
    print("\n💾 步骤3: 保存结果...")
    
    # 保存解码的二进制文件
    bits_to_file(all_data_bits, output_file)
    print(f"   解码数据已保存: {output_file}")
    
    # 保存有效性标记（按字节打包）
    save_vout_bits(all_vout, vout_file)
    print(f"   有效性标记已保存: {vout_file}")
    
    # 4. 清理临时文件
    print("\n🧹 步骤4: 清理临时文件...")
    shutil.rmtree(frames_dir, ignore_errors=True)
    
    # 5. 输出统计信息
    total_bits = len(all_data_bits)
    error_bits = sum(1 for v in all_vout if v == 0)
    
    print("\n" + "=" * 50)
    print(f"✅ 解码完成!")
    print(f"=" * 50)
    print(f"总帧数: {len(frame_files)}")
    print(f"有效帧: {valid_frame_count}")
    print(f"无效帧: {invalid_frame_count}")
    print(f"误帧率: {invalid_frame_count / len(frame_files) * 100:.2f}%" if frame_files else "N/A")
    print(f"解码比特数: {total_bits}")
    print(f"错误比特数: {error_bits}")
    print(f"误码率: {error_bits / total_bits * 100:.2f}%" if total_bits > 0 else "N/A")
    print(f"输出文件大小: {os.path.getsize(output_file)} bytes")
    print(f"=" * 50)


if __name__ == "__main__":
    main()