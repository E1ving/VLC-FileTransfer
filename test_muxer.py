import cv2
import os
import numpy as np
import shutil
import binascii
from utils.VisionCorrector import VisionCorrector
from core.decoder_engine import DecoderEngine
from utils.video_muxer import VideoMuxer

# --- 配置 ---
video_path = "input.mp4"
temp_dir = "temp_frames"
debug_dir = "debug_corrected" 

# 1. 准备环境
for d in [temp_dir, debug_dir]:
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

# 2. 拆解视频
VideoMuxer.video_to_frames(video_path, temp_dir)

# 3. 初始化核心组件
corrector = VisionCorrector()
engine = DecoderEngine()
final_data_bits = []

# 4. 获取文件名并排序
frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith(".png")])
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

# 5. 逐帧处理 (合并逻辑)
for i, f in enumerate(frame_files):
    frame = cv2.imread(os.path.join(temp_dir, f))
    if frame is None:
        continue
    
    # --- A. 视觉校正 ---
    # corrected 应该是 1008x1008 的灰度图
    corrected = corrector.correct(frame)
    
    if corrected is None:
        stats["anchor_fail"] += 1
        continue
    
    if isinstance(corrected, str) and corrected == "SKIP":
        stats["skip"] += 1
        continue

    # --- B. 采样点可视化诊断 (关键修改) ---
    # 先将灰度图转为彩色图以便画红点
    # 修复方案：判断通道数后再转换
    if len(corrected.shape) == 2:
        # 如果是灰度图，转为彩色以便画红绿诊断点
        debug_img = cv2.cvtColor(corrected, cv2.COLOR_GRAY2BGR)
    else:
        # 如果已经是彩色图，直接复制一份用于调试
        debug_img = corrected.copy()
    bs = engine.p.BLOCK_SIZE
    offset = bs // 2 # 6像素偏移

    for r in range(engine.p.ROWS):
        for c in range(engine.p.COLS):
            if engine.p.is_in_anchor_zone(r, c):
                continue 
            
            # 【公式对齐】直接根据行列计算中心，不再手动计算 origin_pos
            x_center = int(c * bs + offset)
            y_center = int(r * bs + offset)
            
            # 画一个极小的红点
            cv2.circle(debug_img, (x_center, y_center), 1, (0, 0, 255), -1)

    # 保存诊断图
    cv2.imwrite(os.path.join(debug_dir, f"diag_{f}"), debug_img)
    
    # --- C. 核心解码 ---
    # ⚠️ 传给 engine 的必须是原始灰度图 corrected
    success, payload = engine.process_frame(corrected) 
    
    if success is True:
        final_data_bits.extend(payload)
        stats["success"] += 1
    elif success == "SKIP":
        stats["skip"] += 1
    else:
        # 详细分析失败原因
        all_bits = engine.frame_to_bits(corrected)
        received_sync = all_bits[:len(engine.p.SYNC_PATTERN)]
        
        if received_sync != engine.p.SYNC_PATTERN:
            stats["sync_fail"] += 1
            if stats["sync_fail"] <= 5: # 打印前5次记录
                print(f"⚠️ {f}: 同步失败 | 收到: {''.join(map(str, received_sync[:8]))}...")
        else:
            stats["crc_fail"] += 1
            if stats["crc_fail"] <= 5:
                print(f"⚠️ {f}: 同步成功，但 CRC 校验不匹配")

# 6. 打印总结报告
print("\n" + "="*40)
print("📊 VLC 链路诊断报告")
print(f"总处理帧数: {stats['total']}")
print("-" * 20)
print(f"❌ 定位失败 (Anchor):  {stats['anchor_fail']} (检查 VisionCorrector 阈值)")
print(f"❌ 同步失败 (Sync):    {stats['sync_fail']} (红点是否在格子正中心？)")
print(f"❌ 校验失败 (CRC):     {stats['crc_fail']} (检查噪点、光线干扰)")
print(f"⏭️  跳过重复 (Skip):    {stats['skip']}")
print(f"✅ 成功解析 (Success): {stats['success']}")
print("-" * 20)
print(f"📦 累计提取有效载荷: {len(final_data_bits)//8} Bytes")
print("="*40)

# 7. 清理缓存
# shutil.rmtree(temp_dir) # 如果需要查看中间帧可以注释掉这行