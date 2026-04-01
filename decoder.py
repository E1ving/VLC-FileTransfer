import sys
import cv2
import os
import shutil
import math
import numpy as np
from core.decoder_engine import DecoderEngine
from utils.VisionCorrector import VisionCorrector
from utils.video_muxer import VideoMuxer

def main():
    if len(sys.argv) < 4:
        print("💡 Usage: python decode.py <recorded.mp4> <out.bin> <vout.bin> [max_ms]")
        sys.exit(1)
    video_path = sys.argv[1]
    out_bin_path = sys.argv[2]
    vout_bin_path = sys.argv[3]

    # 获取发送端的物理参数
    max_ms = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
    tx_fps = 25 

    # 1. 环境初始化
    temp_dir = "temp_decode_frames"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    corrector = VisionCorrector() 
    decoder = DecoderEngine()
    std_capacity = decoder.p.get_data_capacity_per_frame()
    bytes_per_frame = std_capacity // 8
    
    # 2. 视频拆帧
    print(f"🎞️ 正在拆解视频: {video_path}...")
    VideoMuxer.video_to_frames(video_path, temp_dir)
    
    frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith(".png")], 
                         key=lambda x: int(x.split('_')[1].split('.')[0]) if '_' in x else x)
    
    # --- 序号对齐变量 ---
    decoded_packets = {}  # {abs_seq: bits}
    last_raw_seq = -1
    epoch = 0
    finalized_seqs = set()
    
    # 3. 逐帧处理
    success_frame_count = 0
    total_processed = 0

    print(f"🔍 开始解码 {len(frame_files)} 个候选帧 (冗余采样模式)...")
    
    for frame_name in frame_files:
        total_processed += 1
        img = cv2.imread(os.path.join(temp_dir, frame_name))
        if img is None: continue
        
        warped = corrector.correct(img)
        if warped is None or (isinstance(warped, str) and warped == "SKIP"):
            continue 
        
        is_valid, data_payload, raw_seq = decoder.process_frame(warped)
        
        if raw_seq != -1:
            if last_raw_seq != -1 and raw_seq < last_raw_seq - 100:
                epoch += 1
            current_abs_seq = epoch * 256 + raw_seq
            last_raw_seq = raw_seq
        else:
            continue

        if current_abs_seq in finalized_seqs:
            continue

        if is_valid is True:
            decoded_packets[current_abs_seq] = data_payload
            finalized_seqs.add(current_abs_seq)
            success_frame_count += 1

    # 4. 基于序号重组比特流与生成掩码
    print(f"💾 正在根据序号重组并自动补全...")
    all_recovered_bits = []
    all_mask_bits = [] 
    
    if decoded_packets:
        min_seq = 0 
        max_seq = max(decoded_packets.keys())

        for s in range(min_seq, max_seq + 1):
            if s in decoded_packets:
                all_recovered_bits.extend(decoded_packets[s])
                all_mask_bits.extend([1] * len(decoded_packets[s]))
            else:
                all_recovered_bits.extend([0] * std_capacity)
                all_mask_bits.extend([0] * std_capacity)

    # 5. 写入文件
    out_bytes = bytearray()
    for i in range(0, len(all_recovered_bits), 8):
        chunk = all_recovered_bits[i:i+8]
        if len(chunk) < 8: break
        byte_val = 0
        for bit in chunk: byte_val = (byte_val << 1) | bit
        out_bytes.append(byte_val)

    with open(out_bin_path, "wb") as f: f.write(out_bytes)
    
    vout_bytes = bytearray()
    for i in range(0, len(all_mask_bits), 8):
        m_chunk = all_mask_bits[i:i+8]
        if len(m_chunk) < 8: break
        vout_bytes.append(0xFF if all(m_chunk) else 0x00)
    with open(vout_bin_path, "wb") as f: f.write(vout_bytes)

    # 6. 获取时长
    cap = cv2.VideoCapture(video_path)
    cap_fps = cap.get(cv2.CAP_PROP_FPS)
    f_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = f_count / cap_fps if (cap_fps > 0 and f_count > 0) else 8.0
    cap.release()

    # 7. 打印统计结果 (已去掉评估部分)
    print(f"\n" + "="*40)
    print(f"✨ 解码任务圆满完成！")
    print(f"📊 基础统计:")
    print(f"   - 独立有效帧: {success_frame_count}")
    print(f"   - 最终产出:   {len(out_bytes)} Bytes")
    print(f"   - 视频时长:   {duration:.2f} s")
    print("="*40)

    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()