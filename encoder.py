import sys
import os
import shutil
import math
from core.encoder_engine import EncoderEngine
from utils.video_muxer import VideoMuxer

def main():
    # 1. 参数校验
    if len(sys.argv) < 4:
        print("Usage: python encoder.py <in.bin> <out.mp4> <max_ms>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    try:
        max_ms = int(sys.argv[3])
    except ValueError:
        print("❌ 错误：max_ms 必须是整数（毫秒）")
        sys.exit(1)

    # 2. 帧率与容量配置
    fps = 15  # 统一设定为 15 FPS   
    encoder = EncoderEngine()
    # 计算当前 FPS 下允许的最大帧数
    max_frames_allowed = math.floor((max_ms / 1000.0) * fps)
    
    # 每一帧的净载荷是 2864 bits (358 bytes)
    bytes_per_frame = 358 

    # 3. 准备工作环境
    temp_dir = "temp_encode_frames"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # 4. 读取数据
    if not os.path.exists(input_path):
        print(f"❌ 错误：找不到输入文件 {input_path}")
        sys.exit(1)
        
    print(f"📖 读取文件: {input_path}...")
    with open(input_path, "rb") as f:
        full_data = f.read()

    # 计算总共需要的帧数
    total_frames_needed = math.ceil(len(full_data) / bytes_per_frame)
    
    # 【时长检查逻辑】
    if total_frames_needed > max_frames_allowed:
        print(f"⚠️ 警告：数据量庞大，共需 {total_frames_needed} 帧")
        print(f"⏱️  限长 {max_ms}ms ({max_frames_allowed} 帧)，数据将被截断。")
        total_frames = max_frames_allowed
    else:
        total_frames = total_frames_needed
        print(f"✅ 数据适合时长限制: 预计占用 {total_frames} 帧 ({total_frames/fps:.2f} 秒)")

    # 5. 生成图像序列
    # 将 bytes 转为 bits 列表并切片渲染
    print(f"🔄 正在转换并渲染...")
    all_bits = []
    for byte in full_data:
        all_bits.extend([int(b) for b in f"{byte:08b}"])
        
    # 调用引擎处理 (内部处理 CRC 与绘制)
    # 我们只传入前 total_frames 帧对应的数据
    render_bits = all_bits[:total_frames * bytes_per_frame * 8]
    encoder.generate_all_frames(render_bits, output_dir=temp_dir)

    # 6. 调用 FFmpeg 进行无损合成
    print(f"🎬 调用 VideoMuxer 合成 (FPS={fps})...")
    VideoMuxer.ffmpeg_convert(temp_dir, output_path, fps=fps)

    # 7. 清理并退出
    shutil.rmtree(temp_dir)
    print(f"✨ 编码完成！视频已保存至: {output_path}")

if __name__ == "__main__":
    main()