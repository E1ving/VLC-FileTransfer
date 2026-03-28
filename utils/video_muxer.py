import cv2
import os
import subprocess

class VideoMuxer:
    """
    视频流处理模块：独立于编码/解码核心，专注 IO
    """
    
    @staticmethod
    def frames_to_video(frame_dir, output_path, fps=15):
        """使用 OpenCV 合成视频 (已优化)"""
        
        # 获取目录下所有 png 图片并排序
        images = [img for img in os.listdir(frame_dir) if img.endswith(".png")]
        images.sort()
        
        if not images:
            print("❌ 错误：目录下没有图片")
            return

        # 读取第一张图获取尺寸
        frame_path = os.path.join(frame_dir, images[0])
        frame = cv2.imread(frame_path)
        # 获取高度和宽度，抛弃不需要的 layers (通道数)
        height, width = frame.shape[:2] 
        
        # 定义编码器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        # 使用传入的 output_path 参数
        video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        print(f"🎬 开始合成视频... 总帧数: {len(images)}")
        # 在 frames_to_video 的循环中：
        for image_name in images:
            # 【关键修改】强制以灰度模式读取，并确保是 3 通道 BGR 格式
            img = cv2.imread(os.path.join(frame_dir, image_name), cv2.IMREAD_GRAYSCALE)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) 
            video.write(img)
            
        video.release()     
        print(f"✅ 视频合成完毕: {output_path}")

    @staticmethod
    def video_to_frames(video_path, output_dir):
        """使用 OpenCV 拆解视频到文件夹 (供解码器读取)"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        cap = cv2.VideoCapture(video_path)
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imwrite(os.path.join(output_dir, f"frame_{frame_idx:05d}.png"), frame)
            frame_idx += 1
            
        cap.release()
        print(f"✅ 视频拆解完毕，共提取 {frame_idx} 帧")

    @staticmethod
    def ffmpeg_convert(frame_dir, output_path, fps=15):
        """
        进阶：使用 FFmpeg 进行无损编码 (解决压缩伪影问题)   
        当你发现解码 BER 过高时，启用此方法
        """
        cmd = [
            'ffmpeg', '-y', '-framerate', str(fps), 
            '-i', os.path.join(frame_dir, 'frame_%05d.png'),
            '-c:v', 'libx264', '-crf', '0',  # CRF 0 为无损编码
            output_path
        ]
        subprocess.run(cmd)