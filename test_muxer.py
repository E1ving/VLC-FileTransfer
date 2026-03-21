import cv2
import os
import numpy as np
import shutil
from utils.VisionCorrector import VisionCorrector
from core.decoder_engine import DecoderEngine
from utils.video_muxer import VideoMuxer

# --- 配置 ---
video_path = "out.mp4"
temp_dir = "temp_frames"
debug_dir = "debug_corrected" # 用于存放校正后的图片

# 1. 准备环境：清空旧缓存，防止 15帧 vs 290帧 的混淆
for d in [temp_dir, debug_dir]:
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

# 2. 拆分视频（使用 FFmpeg 保证物理帧对齐）
# 注意：VideoMuxer.video_to_frames 内部必须是基于 FFmpeg 的实现
VideoMuxer.video_to_frames(video_path, temp_dir)

# 3. 初始化核心组件
corrector = VisionCorrector()
engine = DecoderEngine()
final_data_bits = []

# 4. 获取文件名并排序
frame_files = sorted([f for f in os.listdir(temp_dir) if f.endswith(".png")])
total_frames = len(frame_files)
print(f"🎬 视频拆解完毕，共提取 {total_frames} 帧。开始解码...")

# 5. 逐帧处理
success_count = 0
print(f"🎬 开始解码...")

for i, f in enumerate(frame_files):
    frame = cv2.imread(os.path.join(temp_dir, f))
    if frame is None:
        continue
    
    # 视觉校正
    corrected = corrector.correct(frame)
    
    # --- 排除 SKIP 信号 ---
    is_skip_signal = isinstance(corrected, str) and corrected == "SKIP"
    if corrected is None or is_skip_signal:
        continue

    # --- 🛠️ 核心修改：在校正后的图上画采样红点 ---
    
    # 1. 创建一个彩色副本用于画红点（因为 corrected 是灰度图）
    debug_sampling_img = corrected.copy()
    
    # 2. 获取协议参数
    block_size = engine.p.BLOCK_SIZE
    
    # 3. 重新计算与 DecoderEngine 完全一致的物理原点 (origin_pos)
    # ⚠️ 注意：这里的逻辑必须与你 DecoderEngine.frame_to_bits 里的公式完全对齐！
    # 假设你采用了 margin = block_size 且逻辑偏移是 1.5
    margin = block_size
    logic_offset = 1.5 * block_size
    origin_pos = margin - logic_offset 

    # 4. 遍历所有网格，计算中心点并画圆
    for r in range(engine.p.ROWS):
        for c in range(engine.p.COLS):
            # 跳过锚点区域（不采样）
            if engine.p.is_in_anchor_zone(r, c):
                continue 
            
            # 计算采样中心坐标 (与 DecoderEngine 公式一致)
            x_center = int(origin_pos + (c * block_size) + (block_size // 2))
            y_center = int(origin_pos + (r * block_size) + (block_size // 2))
            
            # 在彩色副本上画一个实心红点
            # cv2.circle(图像, (x,y), 半径, 颜色(BGR), -1表示实心)
            cv2.circle(debug_sampling_img, (x_center, y_center), 2, (0, 0, 255), -1)

    # 5. 保存带有红点的诊断图片
    debug_path = os.path.join(debug_dir, f"sampling_{f}")
    cv2.imwrite(debug_path, debug_sampling_img)
    
    # --- 后续解码逻辑 (保持不变) ---
    # ⚠️ 注意：传给 engine 的必须是原始灰度图，不能是画了红点的图！
    success, payload = engine.process_frame(corrected) 
    
    if success is True:
        final_data_bits.extend(payload)
        success_count += 1
    elif success == "SKIP":
        continue

# 强制关闭所有 OpenCV 窗口
cv2.destroyAllWindows()

# 如果你想看采样点是否对齐，可以取消注释下面几行：
# if len(final_data_bits) > 0:
#     import binascii
#     print(f"前 10 个字节 (HEX): {binascii.hexlify(engine._bits_to_bytes(final_data_bits[:80]))}")

# 统计变量
stats = {"total": total_frames, "anchor_fail": 0, "skip": 0, "sync_fail": 0, "crc_fail": 0, "success": 0}

for i, f in enumerate(frame_files):
    frame = cv2.imread(os.path.join(temp_dir, f))
    if frame is None: continue
    
    corrected = corrector.correct(frame)
    
    # 1. 定位检查
    if corrected is None:
        stats["anchor_fail"] += 1
        continue
    
    # 2. 去重检查
    if isinstance(corrected, str) and corrected == "SKIP":
        stats["skip"] += 1
        continue

    # 保存诊断图
    cv2.imwrite(os.path.join(debug_dir, f"corrected_{f}"), corrected)
        
    # 3. 深度解码调试
    # 我们调用一个新的调试方法或直接拆解 process_frame 的逻辑
    success, payload = engine.process_frame(corrected)
    
    if success is True:
        final_data_bits.extend(payload)
        stats["success"] += 1
    elif success is False:
        # --- 调试核心：判定具体失败原因 ---
        all_bits = engine.frame_to_bits(corrected)
        received_sync = all_bits[:len(engine.p.SYNC_PATTERN)]
        
        if received_sync != engine.p.SYNC_PATTERN:
            stats["sync_fail"] += 1
            if stats["sync_fail"] <= 3: # 只打印前几次失败，避免刷屏
                print(f"Frame {f}: 同步码错误")
                print(f"  Exp: {engine.p.SYNC_PATTERN}")
                print(f"  Got: {received_sync}")
        else:
            stats["crc_fail"] += 1
            if stats["crc_fail"] <= 3:
                print(f"Frame {f}: 同步码 OK，但 CRC 失败")
    elif success == "SKIP":
        stats["skip"] += 1

# --- 打印诊断报告 ---
print("\n" + "="*30)
print("📊 最终诊断报告")
print(f"总处理帧数: {stats['total']}")
print(f"1. 定位失败 (Anchor Fail): {stats['anchor_fail']} - 检查定位点或阈值")
print(f"2. 同步失败 (Sync Fail):   {stats['sync_fail']}   - 检查采样偏移 (Offset)")
print(f"3. 校验失败 (CRC Fail):    {stats['crc_fail']}    - 检查采样精度或干扰")
print(f"4. 成功解析 (Success):     {stats['success']}")
print(f"总计提取数据: {len(final_data_bits)//8} 字节")
print("="*30)