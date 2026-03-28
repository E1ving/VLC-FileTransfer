import os
import shutil
import math
from core.encoder_engine import EncoderEngine
from utils.video_muxer import VideoMuxer

# 模拟编码过程
def test_encoding_process():
    # 模拟参数
    input_path = "data/test.bin"
    output_path = "output_test.avi"
    max_ms = 10000
    fps = 15
    
    # 初始化引擎
    encoder = EncoderEngine()
    
    # 计算每帧容量
    bits_per_frame = encoder.p.get_data_capacity_per_frame()
    bytes_per_frame = bits_per_frame // 8
    print(f"每帧容量: {bits_per_frame} bits ({bytes_per_frame} bytes)")
    
    # 计算最大允许帧数
    max_frames_allowed = math.floor((max_ms / 1000.0) * fps)
    print(f"最大允许帧数: {max_frames_allowed}")
    
    # 准备临时目录
    temp_dir = "temp_test_frames"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # 读取测试数据
    if not os.path.exists(input_path):
        print(f"错误：找不到输入文件 {input_path}")
        return
    
    print(f"读取文件: {input_path} ({os.path.getsize(input_path)} Bytes)")
    with open(input_path, "rb") as f:
        full_data = f.read()
    
    # 计算总帧数
    total_frames_needed = math.ceil(len(full_data) / bytes_per_frame)
    print(f"需要的总帧数: {total_frames_needed}")
    
    # 检查时长限制
    if total_frames_needed > max_frames_allowed:
        print(f"警告：数据量庞大，共需 {total_frames_needed} 帧")
        print(f"时长限制 {max_ms}ms ({max_frames_allowed} 帧)，数据将被截断。")
        total_frames = max_frames_allowed
    else:
        total_frames = total_frames_needed
        print(f"数据适合时长限制: 预计占用 {total_frames} 帧 ({total_frames/fps:.2f} 秒)")
    
    # 提取数据并转为比特流
    data_to_encode = full_data[:total_frames * bytes_per_frame]
    print(f"实际编码数据大小: {len(data_to_encode)} Bytes")
    
    # 转换为比特列表
    all_bits = []
    for byte in data_to_encode:
        all_bits.extend([int(b) for b in f"{byte:08b}"])
    print(f"总比特数: {len(all_bits)}")
    
    # 生成帧
    encoder.generate_all_frames(all_bits, output_dir=temp_dir)
    
    # 检查生成的帧数量
    generated_frames = len([f for f in os.listdir(temp_dir) if f.endswith('.png')])
    print(f"生成的帧数量: {generated_frames}")
    print(f"计算的总帧数: {total_frames}")
    
    # 验证帧数量
    if generated_frames != total_frames:
        print("警告：生成的帧数量与计算的总帧数不一致")
    else:
        print("生成的帧数量与计算的总帧数一致")
    
    # 合成视频
    print("开始合成视频...")
    VideoMuxer.frames_to_video(temp_dir, output_path, fps=fps, resize_factor=0.5)
    
    # 清理临时目录
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    print("测试完成！")

if __name__ == "__main__":
    test_encoding_process()
