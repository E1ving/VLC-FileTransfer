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
        print("💡 Usage: python decode.py <recorded.mp4> <out.bin> <vout.bin> [gt.bin]")
        sys.exit(1)

    video_path = sys.argv[1]
    out_bin_path = sys.argv[2]
    vout_bin_path = sys.argv[3]
    gt_bin_path = "in.bin" # 默认读取当前目录下的源文件进行评估

    # 1. 环境初始化
    temp_dir = "temp_decode_frames"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    corrector = VisionCorrector() 
    decoder = DecoderEngine()
    std_capacity = decoder.p.get_data_capacity_per_frame()
    
    # 2. 视频拆帧
    print(f"🎞️ 正在拆解视频: {video_path}...")
    VideoMuxer.video_to_frames(video_path, temp_dir)
    
    frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith(".png")], 
                         key=lambda x: int(x.split('_')[1].split('.')[0]) if '_' in x else x)
    
    # --- 序号对齐变量 ---
    decoded_packets = {}  # {abs_seq: bits}
    last_raw_seq = -1
    epoch = 0
    
    # 3. 逐帧处理
    success_frame_count = 0
    total_processed = 0

    # 新增：记录已经成功采集到的序号，避免重复计算和报错
    finalized_seqs = set()
    
    print(f"🔍 开始解码 {len(frame_files)} 个候选帧 (60fps 冗余采样模式)...")
    
    for frame_name in frame_files:
        total_processed += 1
        img = cv2.imread(os.path.join(temp_dir, frame_name))
        if img is None: continue
        
        # --- 优化 A: 快速视觉矫正 ---
        warped = corrector.correct(img)
        if warped is None or (isinstance(warped, str) and warped == "SKIP"):
            continue 
        
        # --- 优化 B: 提取序号并进行“查重” ---
        # 预先提取序号（这里可以调低校验严格度先拿 Seq，或者直接调 process_frame）
        is_valid, data_payload, raw_seq = decoder.process_frame(warped)
        
        # 处理序号回绕得到绝对序号
        if raw_seq != -1:
            if last_raw_seq != -1 and raw_seq < last_raw_seq - 100:
                epoch += 1
            current_abs_seq = epoch * 256 + raw_seq
            last_raw_seq = raw_seq
        else:
            continue

        # --- 核心逻辑：首胜制 (First Success Wins) ---
        if current_abs_seq in finalized_seqs:
            # 如果这一帧已经成功拿到了，直接跳过，不再进行后续 CRC 报错或处理
            continue

        if is_valid is True:
            # 这一帧是该序号下的第一个“幸运儿”
            decoded_packets[current_abs_seq] = data_payload
            finalized_seqs.add(current_abs_seq)
            success_frame_count += 1
            # print(f"✅ 序号 {current_abs_seq} 采集成功 (来自帧 {frame_name})")
        
        # 如果 is_valid 不是 True，我们不需要打印错误，因为后面可能还有该序号的备份帧

    # 4. 基于序号重组比特流与生成掩码
    print(f"💾 正在根据序号重组并自动补全...")
    all_recovered_bits = []
    all_mask_bits = [] # 记录哪些位是补全的(0)，哪些是真实的(1)
    
    if decoded_packets:
        min_seq = min(decoded_packets.keys())
        max_seq = max(decoded_packets.keys())

        for s in range(min_seq, max_seq + 1):
            if s in decoded_packets:
                all_recovered_bits.extend(decoded_packets[s])
                all_mask_bits.extend([1] * len(decoded_packets[s]))
            else:
                # 发现空洞，填充 0 并标记为无效 (mask=0)
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
    
    # 生成 vout.bin (基于 mask 统计，每 8 位全有效则为 0xFF)
    vout_bytes = bytearray()
    for i in range(0, len(all_mask_bits), 8):
        m_chunk = all_mask_bits[i:i+8]
        if len(m_chunk) < 8: break
        vout_bytes.append(0xFF if all(m_chunk) else 0x00)
    with open(vout_bin_path, "wb") as f: f.write(vout_bytes)

    # 6. 获取时长
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    f_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = f_count / fps if (fps > 0 and f_count > 0) else 8.0 # 保底 8s
    cap.release()

    # 7. --- 集成评估逻辑 ---
    print(f"\n" + "="*40)
    print(f"✨ 解码任务圆满完成！")
    
    if gt_bin_path and os.path.exists(gt_bin_path):
        with open(gt_bin_path, 'rb') as f:
            gt_data = np.frombuffer(f.read(), dtype=np.uint8)
        gt_bits = np.unpackbits(gt_data)
        
        # 对齐长度
        min_len = min(len(gt_bits), len(all_recovered_bits))
        rec_bits_arr = np.array(all_recovered_bits[:min_len])
        gt_bits_arr = np.array(gt_bits[:min_len])
        mask_bits_arr = np.array(all_mask_bits[:min_len])

        # 丢失率与误码率
        erasure_rate = np.sum(mask_bits_arr == 0) / min_len
        undetected_errors = (rec_bits_arr != gt_bits_arr) & (mask_bits_arr == 1)
        ber = np.sum(undetected_errors) / min_len

        # 有效传输量 (首个漏检错误前的正确位)
        error_indices = np.where(undetected_errors == True)[0]
        effective_bits = error_indices[0] if len(error_indices) > 0 else np.sum(mask_bits_arr)
        
        bps = effective_bits / duration

        print(f"📊 严格评估报告 (对标 {os.path.basename(gt_bin_path)}):")
        print(f"   - 有效传输量: {int(effective_bits)} bits")
        print(f"   - 有效传输率: {bps / 1000:.2f} kbps")
        print(f"   - 误码率 (BER): {ber:.6%}")
        print(f"   - 丢失率 (Erasure): {erasure_rate:.2%}")
    
    print(f"📊 基础统计:")
    print(f"   - 独立有效帧: {success_frame_count}")
    print(f"   - 最终产出:   {len(out_bytes)} Bytes")
    print(f"   - 视频时长:   {duration:.2f} s")
    print("="*40)

    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()