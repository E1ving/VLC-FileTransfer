import sys
import cv2
import os
import shutil
import numpy as np
from core.decoder_engine import DecoderEngine
from utils.VisionCorrector import VisionCorrector
from utils.video_muxer import VideoMuxer

def main():
    if len(sys.argv) < 4:
        print("Usage: python decode.py <recorded.mp4> <out.bin> <vout.bin>")
        sys.exit(1)

    video_path = sys.argv[1]
    out_bin_path = sys.argv[2]
    vout_bin_path = sys.argv[3]

    # 1. 准备环境与初始化
    temp_dir = "temp_decode_frames"
    corrector = VisionCorrector() 
    decoder = DecoderEngine()
    
    # 2. 视频拆帧
    print(f"🎞️ 正在拆解视频: {video_path}...")
    VideoMuxer.video_to_frames(video_path, temp_dir)
    
    frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith(".png")])
    
    all_recovered_bits = []
    validity_masks = [] 

    # 3. 逐帧处理
    success_frame_count = 0
    duplicate_count = 0
    
    print(f"🔍 开始解码 {len(frame_files)} 个帧...")
    for frame_name in frame_files:
        frame_path = os.path.join(temp_dir, frame_name)
        img = cv2.imread(frame_path)
        if img is None: continue
        
        # --- A. 第一级去重：视觉哈希 (VisionCorrector) ---
        # 这一步过滤掉由于视频编码或相机快门产生的“物理纯重复”帧
        warped = corrector.correct(img)

        # 使用 isinstance 判断是否为字符串 "SKIP"
        if isinstance(warped, str) and warped == "SKIP":
            duplicate_count += 1
            continue
            
        if warped is None:
            # 定位失败，可能是对焦模糊或光影干扰
            continue 
        
        # --- B. 第二级去重与校验：帧序号 & CRC (DecoderEngine) ---
        # is_valid 的可能取值: True (正常), False (CRC失败), "SKIP" (序号重复)
        is_valid, data_payload = decoder.process_frame(warped)
        
        if is_valid == "SKIP":
            # 命中业务逻辑去重（画面变了但序号没变，通常是手机传感器的热噪声导致）
            duplicate_count += 1
            continue
            
        if not is_valid:
            # 校验失败
            print(f"❌ 校验失败 (帧: {frame_name})")
            continue
        
        # --- C. 采纳数据 ---
        # data_payload 已经是根据 LEN 字段裁剪过的精确比特流
        all_recovered_bits.extend(data_payload)
        
        # 更新有效性掩码 (按字节对齐)
        bytes_added = len(data_payload) // 8
        if bytes_added > 0:
            validity_masks.extend([0xFF] * bytes_added)
        
        success_frame_count += 1
        # 实时打印进度
        if success_frame_count % 5 == 0:
            print(f"✅ 已采纳 {success_frame_count} 帧, 累计数据: {len(all_recovered_bits)//8} Bytes")
        
    # 4. 写入二进制文件
    print(f"💾 正在写入输出文件...")
    
    out_bytes = bytearray()
    for i in range(0, len(all_recovered_bits), 8):
        byte_bits = all_recovered_bits[i:i+8]
        if len(byte_bits) < 8: break # 忽略不足一字节的末尾
        byte_val = int("".join(map(str, byte_bits)), 2)
        out_bytes.append(byte_val)

    with open(out_bin_path, "wb") as f:
        f.write(out_bytes)
        
    with open(vout_bin_path, "wb") as f:
        # 如果有散碎位不满足一字节，对齐掩码长度
        f.write(bytearray(validity_masks))

    # 5. 清理
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    print(f"✨ 解码任务完成！")
    print(f"📊 统计: 采纳新帧: {success_frame_count} | 过滤重复: {duplicate_count} | 总数据: {len(out_bytes)} Bytes")

if __name__ == "__main__":
    main()