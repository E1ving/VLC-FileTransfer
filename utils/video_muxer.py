import cv2
import os
import subprocess

class VideoMuxer:
    """
    视频流处理模块：独立于编码/解码核心，专注 IO
    """
    
    @staticmethod
    def frames_to_video(frame_dir, output_path, fps=15, resize_factor=1.0):
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
        
        # 调整视频大小
        new_width = int(width * resize_factor)
        new_height = int(height * resize_factor)
        
        # 定义编码器，使用H.264编码器（与output.mp4相同）
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        # 使用传入的 output_path 参数
        video = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
        
        # 如果H.264不可用，尝试其他编码器
        if not video.isOpened():
            print("⚠️ H.264编码器不可用，尝试使用MJPG编码器...")
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            video = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
            
            if not video.isOpened():
                print("⚠️ MJPG编码器不可用，尝试使用MP4V编码器...")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
        
        print(f"🎬 开始合成视频... 总帧数: {len(images)}")
        # 在 frames_to_video 的循环中：
        for image_name in images:
            # 直接读取原始图像
            img = cv2.imread(os.path.join(frame_dir, image_name))
            
            # 调整图像大小
            if resize_factor != 1.0:
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_NEAREST)
                
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
            cv2.imwrite(os.path.join(output_dir, f"frame_{frame_idx:04d}.png"), frame)
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
            '-i', os.path.join(frame_dir, 'frame_%04d.png'),
            '-c:v', 'libx264', '-crf', '0',  # CRF 0 为无损编码
            output_path
        ]
        subprocess.run(cmd)