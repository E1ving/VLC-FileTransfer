from utils.video_muxer import VideoMuxer
import os
import shutil

# 转换视频格式
def convert_video(input_path, output_path):
    # 创建临时目录
    temp_dir = "temp_frames"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # 拆解视频到帧
    print(f"🔄 正在拆解视频 {input_path}...")
    VideoMuxer.video_to_frames(input_path, temp_dir)
    
    # 合成视频为.mp4格式
    print(f"🎬 正在合成视频 {output_path}...")
    VideoMuxer.frames_to_video(temp_dir, output_path, fps=15, resize_factor=1.0)
    
    # 清理临时目录
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    print(f"✅ 视频转换完成: {output_path}")

if __name__ == "__main__":
    # 转换output.avi为output.mp4
    convert_video("output.avi", "output.mp4")
