# src/protocol/frame_config.py

# 从物理参数文件导入计算得出的值
from src.physical_params import ADJUSTED_PAYLOAD_LENGTH

# --- 帧结构设计 ---
# 1. 同步码 (Synchronization Code): 用于接收端识别帧头
# 选择一个不易在数据中随机出现的序列，例如 8 bit: 10101010 (0xAA) 或更长
SYNC_CODE = [1, 0, 1, 0, 1, 0, 1, 0] 
SYNC_CODE_LENGTH = len(SYNC_CODE)

# 2. 帧头其他信息 (可选): 如序列号 (Sequence Number)
# 假设用 8 bit 表示序列号 (0-255)，用于王皓琳判断丢帧/重帧
SEQ_NUM_LENGTH = 8 

# 3. 数据载荷 (Payload): 每一帧携带的有效数据比特数
# 已根据物理参数调整，确保是8的倍数，方便CRC校验
PAYLOAD_LENGTH = ADJUSTED_PAYLOAD_LENGTH

# 4. 校验码 (Checksum/CRC): 帧尾
# 使用 CRC-8 或简单的异或校验？为了鲁棒性，建议使用 CRC-8
# 这里定义校验位长度
CHECKSUM_LENGTH = 8 

# --- 计算总帧长 ---
FRAME_TOTAL_LENGTH = SYNC_CODE_LENGTH + SEQ_NUM_LENGTH + PAYLOAD_LENGTH + CHECKSUM_LENGTH

# --- 协议版本 ---
PROTOCOL_VERSION = "v1.0-Huo-adjusted"