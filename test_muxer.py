import cv2
import os
import numpy as np
import shutil
import sys
from utils.VisionCorrector import VisionCorrector
from core.decoder_engine import DecoderEngine
from utils.video_muxer import VideoMuxer

# --- 配置 ---
video_path = "01_out.mp4" # 建议确保视频文件存在
temp_dir = "temp_frames"
debug_dir = "debug_corrected" 

# 1. 准备环境
for d in [temp_dir, debug_dir]:
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

# 2. 拆解视频
print(f"🎞️ 正在拆解视频: {video_path}...")
VideoMuxer.video_to_frames(video_path, temp_dir)

# 3. 初始化核心组件
corrector = VisionCorrector()
engine = DecoderEngine()
final_data_bits = []

# 4. 获取文件名并排序
frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith(".png")],
                     key=lambda x: int(x.split('_')[1].split('.')[0]) if '_' in x else x)
total_frames = len(frame_files)

# 统计变量
stats = {
    "total": total_frames, 
    "anchor_fail": 0, 
    "skip": 0, 
    "sync_fail": 0, 
    "crc_fail": 0, 
    "success": 0
}

print(f"🎬 视频拆解完毕，共提取 {total_frames} 帧。开始合并诊断解码...")

# 5. 逐帧处理
for i, f in enumerate(frame_files):
    frame_path = os.path.join(temp_dir, f)
    frame = cv2.imread(frame_path)
    if frame is None:
        continue
    
    # --- A. 视觉校正 ---
    corrected = corrector.correct(frame)
    
    if corrected is None:
        stats["anchor_fail"] += 1
        continue
    
    if isinstance(corrected, str) and corrected == "SKIP":
        stats["skip"] += 1
        continue

    # --- B. 采样点可视化诊断 ---
    # 确保是彩色图用于画红点
    if len(corrected.shape) == 2:
        debug_img = cv2.cvtColor(corrected, cv2.COLOR_GRAYBGR)
    else:
        debug_img = corrected.copy()

    bs = engine.p.BLOCK_SIZE
    offset = bs // 2 

    # 遍历所有格子并在中心画点
    for r in range(engine.p.ROWS):
        for c in range(engine.p.COLS):
            # 虽然 Anchor 区不存数据，但画出来可以检查对齐准不准
            x_center = int(c * bs + offset)
            y_center = int(r * bs + offset)
            
            # 画一个极小的红点 (半径1, 红色, 实心)
            cv2.circle(debug_img, (x_center, y_center), 1, (0, 0, 255), -1)

    # 保存诊断图到 debug_dir
    cv2.imwrite(os.path.join(debug_dir, f"diag_{f}"), debug_img)
    
    # --- C. 核心解码 (修复 ValueError) ---
    # ⚠️ 必须接收 3 个值：is_valid, payload, raw_seq
    is_valid, payload, raw_seq = engine.process_frame(corrected) 
    
    if is_valid is True:
        final_data_bits.extend(payload)
        stats["success"] += 1
    elif is_valid == "SKIP":
        stats["skip"] += 1
    else:
        # 详细分析失败原因：手动提取比特进行同步头比对
        all_bits = engine.frame_to_bits(corrected)
        sync_len = len(engine.p.SYNC_PATTERN)
        received_sync = all_bits[:sync_len]
        
        if not np.array_equal(received_sync, engine.p.SYNC_PATTERN):
            stats["sync_fail"] += 1
            if stats["sync_fail"] <= 3:
                print(f"⚠️ {f}: 同步失败 | 收到: {received_sync[:8]}... 期待: {engine.p.SYNC_PATTERN[:8]}")
        else:
            stats["crc_fail"] += 1
            if stats["crc_fail"] <= 3:
                print(f"⚠️ {f}: 同步成功，但序号 {raw_seq} 的 CRC 校验失败")

# 6. 打印总结报告
print("\n" + "="*40)
print("📊 VLC 链路诊断报告")
print(f"总处理帧数: {stats['total']}")
print("-" * 20)
print(f"❌ 定位失败 (Anchor):  {stats['anchor_fail']}")
print(f"❌ 同步失败 (Sync):    {stats['sync_fail']}")
print(f"❌ 校验失败 (CRC):     {stats['crc_fail']}")
print(f"⏭️  跳过/重复 (Skip):   {stats['skip']}")
print(f"✅ 成功解析 (Success): {stats['success']}")
print("-" * 20)
print(f"📦 累计提取有效载荷: {len(final_data_bits)//8} Bytes")
print("="*40)