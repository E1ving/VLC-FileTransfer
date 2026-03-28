import sys
import os
import shutil
import math
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

    # 2. 初始化引擎与容量配置
    fps = 25  # 调整帧率到25，在20-30之间
    encoder = EncoderEngine()
    
    # 【动态获取容量】不再硬编码 358 bytes
    # 根据你的 1000x1000 协议计算出的每帧纯数据位宽
    from core.protocol import OpticalProtocol as p
    bits_per_frame = p.get_data_capacity_per_frame()
    bytes_per_frame = bits_per_frame // 8
    
    # 计算当前时长限制下的最大允许帧数
    max_frames_allowed = math.floor((max_ms / 1000.0) * fps)
    
    # 3. 准备工作环境
    temp_dir = "temp_encode_frames"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # 4. 读取数据并计算分片
    if not os.path.exists(input_path):
        print(f"❌ 错误：找不到输入文件 {input_path}")
        sys.exit(1)
        
    print(f"📖 读取文件: {input_path} ({os.path.getsize(input_path)} Bytes)")
    with open(input_path, "rb") as f:
        full_data = f.read()

    # 计算总共需要的帧数
    total_frames_needed = math.ceil(len(full_data) / bytes_per_frame)
    
    # 【时长检查与截断逻辑】
    if total_frames_needed > max_frames_allowed:
        print(f"⚠️ 警告：数据量庞大，共需 {total_frames_needed} 帧")
        print(f"⏱️  时长限制 {max_ms}ms ({max_frames_allowed} 帧)，数据将被截断。")
        total_frames = max_frames_allowed
    else:
        total_frames = total_frames_needed
        print(f"✅ 数据适合时长限制: 预计占用 {total_frames} 帧 ({total_frames/fps:.2f} 秒)")

    # 5. 提取需要编码的数据并转为比特流
    # 截取数据以适应帧数限制
    data_to_encode = full_data[:total_frames * bytes_per_frame]
    
    print(f"🔄 正在转换为比特流并渲染图像序列...")
    
    # 高效转换为比特列表
    all_bits = []
    for byte in data_to_encode:
        # 确保使用 8位对齐，大端序 (MSB first)
        all_bits.extend([int(b) for b in f"{byte:08b}"])
        
    # 6. 调用引擎生成图像
    # generate_all_frames 内部会处理：
    # [每帧切片] -> [添加 Header(SYNC/SEQ/LEN)] -> [计算 CRC] -> [绘制 1008x1008 矩阵]
    encoder.generate_all_frames(all_bits, output_dir=temp_dir)
    
    # 检查生成的帧数量
    generated_frames = len([f for f in os.listdir(temp_dir) if f.endswith('.png')])
    print(f"🔍 生成的帧数量: {generated_frames}")
    print(f"📊 计算的总帧数: {total_frames}")
    
    # 验证帧数量是否一致
    if generated_frames != total_frames:
        print("⚠️ 警告：生成的帧数量与计算的总帧数不一致")
        print(f"   生成的帧数量: {generated_frames}")
        print(f"   计算的总帧数: {total_frames}")
    else:
        print("✅ 生成的帧数量与计算的总帧数一致")

    # 7. 使用OpenCV合成视频 (确保兼容性)
    # 必须无损，否则 12px 的格子边缘会因为压缩产生虚影导致解码失败
    print(f"🎬 调用 VideoMuxer (OpenCV) 合成视频...")
    # 调整视频大小为原始的50%，保持定位点完整
    VideoMuxer.frames_to_video(temp_dir, output_path, fps=fps, resize_factor=0.5)
    print(f"📂 视频已保存至: {output_path}")

    # 8. 清理并退出
    # 暂时保留临时目录，以便检查帧文件数量
    # if os.path.exists(temp_dir):
    #     shutil.rmtree(temp_dir)
        
    print(f"✨ 编码任务圆满完成！")
    print(f"📊 报告: 原始大小 {len(full_data)}B | 实际打包 {len(data_to_encode)}B | 总帧数 {total_frames}")
    print(f"📂 视频已保存至: {output_path}")

if __name__ == "__main__":
    main()