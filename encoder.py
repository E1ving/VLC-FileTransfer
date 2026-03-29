import sys
import os
import shutil
import math
import numpy as np
from core.encoder_engine import EncoderEngine
from utils.video_muxer import VideoMuxer

def main():
    # 1. 参数校验
    if len(sys.argv) < 4:
        print("💡 Usage: python encoder.py <in.bin> <out.mp4> <max_ms>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    try:
        max_ms = int(sys.argv[3])
    except ValueError:
        print("❌ 错误：max_ms 必须是整数（毫秒）")
        sys.exit(1)

    # 2. 初始化引擎
    fps = 25  
    encoder = EncoderEngine()
    bits_per_frame = encoder.p.get_data_capacity_per_frame()
    bytes_per_frame = bits_per_frame // 8
    
    # 3. 计算物理窗口限制
    max_frames_allowed = math.floor((max_ms / 1000.0) * fps)
    file_size = os.path.getsize(input_path)
    total_frames_needed = math.ceil(file_size / bytes_per_frame)

    # 最终决定的生成帧数：严格受限于 max_ms
    total_frames = min(total_frames_needed, max_frames_allowed)

    print(f"📖 读取文件: {input_path} ({file_size} Bytes)")
    print(f"⏱️  时长限制: {max_ms}ms | 最大允许帧数: {max_frames_allowed}")
    print(f"📦 实际将生成: {total_frames} 帧 (约 {total_frames/fps:.2f} 秒)")

    # 4. 准备工作环境
    temp_dir = "temp_encode_frames"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # 5. 流式读取并渲染 (只读到 total_frames 为止)
    with open(input_path, "rb") as f:
        for frame_idx in range(total_frames):
            chunk = f.read(bytes_per_frame)
            if not chunk:
                break
            
            # 高效转换比特 (MSB First)
            frame_bits = np.unpackbits(np.frombuffer(chunk, dtype=np.uint8))
            frame_bits_list = frame_bits.tolist()

            # 渲染并保存
            save_path = os.path.join(temp_dir, f"frame_{frame_idx:05d}.png")
            encoder.generate_single_frame(frame_bits_list, frame_idx % 256, save_path)
            
            if frame_idx % 20 == 0:
                print(f" 进度: {frame_idx}/{total_frames} 帧渲染完成...", end='\r')

    # 6. 合成视频
    print(f"\n🎬 调用 VideoMuxer 合成无损视频...")
    VideoMuxer.ffmpeg_convert(temp_dir, output_path, fps=fps)

    # 7. 清理
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    print(f"✨ 编码任务圆满完成！已截断多余数据。")

if __name__ == "__main__":
    main()