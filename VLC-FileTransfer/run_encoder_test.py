# run_encoder_test.py

import sys
import os

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录（run_encoder_test.py 的父目录）
project_root = os.path.dirname(current_dir)
# 将项目根目录添加到 Python 的模块搜索路径中
sys.path.insert(0, project_root)

# 现在可以从项目根目录开始导入了
from src.protocol.encoder import ProtocolEncoder
from src.protocol.frame_config import SYNC_CODE, PAYLOAD_LENGTH, FRAME_TOTAL_LENGTH

def main():
    print("--- 开始测试协议编码器 (物理参数调整后) ---")
    
    encoder = ProtocolEncoder()
    # 模拟一段原始数据 (长度为PAYLOAD_LENGTH的倍数，例如2帧)
    raw_data_length = PAYLOAD_LENGTH * 2 + 10 # 两帧完整数据 + 10 bit
    raw_data = [1] * raw_data_length 
    frames = encoder.encode_stream(raw_data)
    
    print(f"协议版本: 已加载")
    print(f"总帧数: {len(frames)}")
    print(f"单帧结构长度: {len(frames[0])} bits (预期: {FRAME_TOTAL_LENGTH})")
    print(f"每帧数据载荷长度: {PAYLOAD_LENGTH} bits (预期: 8的倍数, 实际: {PAYLOAD_LENGTH % 8 == 0})")
    print(f"第一帧内容 (前20位): {frames[0][:20]} ... (同步码应为 {SYNC_CODE})")
    
    print("\n--- 测试单帧封装 ---")
    test_payload = [1] * PAYLOAD_LENGTH # 创建一个刚好 PAYLOAD_LENGTH bit 的载荷
    single_frame = encoder.encode_frame(test_payload)
    print(f"单帧长度: {len(single_frame)} bits (预期: {FRAME_TOTAL_LENGTH})")
    print(f"同步码匹配: {single_frame[:8] == SYNC_CODE}")
    
    print("\n--- 测试完成 ---")

if __name__ == "__main__":
    main()