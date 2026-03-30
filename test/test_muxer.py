import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import cv2
import numpy as np
from utils.video_muxer import VideoMuxer
from core.encoder_engine import EncoderEngine
from core.protocol import OpticalProtocol as P

def test_muxer_loop():
    # 1. 准备测试环境
    frame_dir = "temp_frames"
    extracted_dir = "temp_extracted"
    video_path = "test_loop.mp4"
    
    # 清理旧数据
    for d in [frame_dir, extracted_dir]:
        if os.path.exists(d): shutil.rmtree(d)
    if os.path.exists(video_path): os.remove(video_path)
    os.makedirs(frame_dir)
    
    encoder = EncoderEngine()
    
    # 2. 生成 5 帧符合协议的图像
    print("🎨 生成符合协议的测试帧...")
    capacity = P.get_data_capacity_per_frame()
    crc_bits = P.CRC_BITS
    total_bits = capacity + crc_bits
    
    for i in range(5):
        base_frame = encoder.create_base_frame()
        # 生成随机数据（使用协议定义的总位数）
        bits = np.random.randint(0, 2, total_bits).tolist()
        frame_img = encoder.draw_data(base_frame, bits)
        # 确保图片保存为 8 位灰度图
        cv2.imwrite(os.path.join(frame_dir, f"frame_{i:04d}.png"), frame_img)
    
    # 3. 合成视频 (必须使用 FFmpeg 无损模式)
    print("🎬 合成无损视频...")
    VideoMuxer.ffmpeg_convert(frame_dir, video_path, fps=60)
    
    # 4. 拆解视频
    print("🎥 拆解视频帧...")
    VideoMuxer.video_to_frames(video_path, extracted_dir)
    
    # 5. 校验：比对原图与拆解图
    print("🔍 开始像素级一致性校验...")
    match_all = True
    for i in range(5):
        orig = cv2.imread(os.path.join(frame_dir, f"frame_{i:04d}.png"), cv2.IMREAD_GRAYSCALE)
        ext = cv2.imread(os.path.join(extracted_dir, f"frame_{i:04d}.png"), cv2.IMREAD_GRAYSCALE)
        
        if orig is None or ext is None:
            print(f"❌ 错误：无法读取第 {i} 帧")
            match_all = False; break
            
        if not np.array_equal(orig, ext):
            # 计算差异像素数
            diff = np.sum(orig != ext)
            print(f"❌ 第 {i} 帧数据不匹配！不同像素点: {diff}")
            match_all = False
            break
            
    if match_all:
        print("🎉 Muxer 模块测试通过！无损链路逻辑正确。")
    else:
        print("⚠️ 校验未通过，请检查 FFmpeg 是否已安装，或是否支持无损编码。")

if __name__ == "__main__":
    test_muxer_loop()