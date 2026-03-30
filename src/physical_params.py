# src/physical_params.py

# --- 物理参数规定 ---

# 1. 视频/图像规格
VIDEO_RESOLUTION_WIDTH = 1920  # 1920p 宽度
VIDEO_RESOLUTION_HEIGHT = 1080 # 1080p 高度
VIDEO_FPS = 60                 # 帧率

# 2. 比特到像素的映射
# 一个 bit 用一个 N x M 的像素块表示
BIT_PIXEL_WIDTH = 2  # 每个bit水平占用2个像素
BIT_PIXEL_HEIGHT = 2 # 每个bit垂直占用2个像素
PIXEL_PER_BIT_AREA = BIT_PIXEL_WIDTH * BIT_PIXEL_HEIGHT # 每个bit占用的总像素数

# 3. 计算单张图像承载的总数据量
# 需要考虑锚点占据的空间
# 假设锚点占用边框一圈，留出内部区域用于数据
MARGIN_PX = 20  # 边距，用于放置锚点，单位：像素
DATA_AREA_WIDTH = VIDEO_RESOLUTION_WIDTH - 2 * MARGIN_PX
DATA_AREA_HEIGHT = VIDEO_RESOLUTION_HEIGHT - 2 * MARGIN_PX

# 计算数据区域内能放多少个bit
BITS_PER_ROW = DATA_AREA_WIDTH // BIT_PIXEL_WIDTH
BITS_PER_COL = DATA_AREA_HEIGHT // BIT_PIXEL_HEIGHT
TOTAL_BITS_PER_IMAGE = BITS_PER_ROW * BITS_PER_COL

# 4. 校验：确保总比特数是8的倍数，方便后续CRC处理
print(f"物理参数计算结果:")
print(f"- 图像分辨率: {VIDEO_RESOLUTION_WIDTH}x{VIDEO_RESOLUTION_HEIGHT}")
print(f"- 每bit占用像素: {BIT_PIXEL_WIDTH}x{BIT_PIXEL_HEIGHT}")
print(f"- 数据区域大小: {DATA_AREA_WIDTH}px x {DATA_AREA_HEIGHT}px")
print(f"- 每行可容纳bit数: {BITS_PER_ROW}")
print(f"- 每列可容纳bit数: {BITS_PER_COL}")
print(f"- 单图总bit数: {TOTAL_BITS_PER_IMAGE}")
print(f"- 总bit数是否为8的倍数: {TOTAL_BITS_PER_IMAGE % 8 == 0}")

# --- 关键：调整PAYLOAD_LENGTH ---
# 如果希望一帧图像只传送一个数据帧，那么PAYLOAD_LENGTH应该 <= TOTAL_BITS_PER_IMAGE
# 但考虑到帧头帧尾，实际可用数据位是 TOTAL_BITS_PER_IMAGE - 头部开销
# 假设头尾共占用 24 bit (SYNC:8 + SEQ:8 + CRC:8)，则可用数据为 TOTAL_BITS_PER_IMAGE - 24
# 并且这个数要足够大才有意义，也要是8的倍数
HEAD_AND_TAIL_OVERHEAD = 24 # 估算的头尾开销
AVAILABLE_PAYLOAD_BITS = TOTAL_BITS_PER_IMAGE - HEAD_AND_TAIL_OVERHEAD

# 为了满足8的倍数要求，向下取整到最近的8的倍数
# 这个值应该赋给 src.protocol.frame_config.PAYLOAD_LENGTH
ADJUSTED_PAYLOAD_LENGTH = (AVAILABLE_PAYLOAD_BITS // 8) * 8
print(f"- 估算可用数据位: {AVAILABLE_PAYLOAD_BITS}")
print(f"- 调整后PAYLOAD_LENGTH (8倍数): {ADJUSTED_PAYLOAD_LENGTH}")


# 5. 视觉锚点规格
ANCHOR_SIZE_PX = 40  # 锚点边长，单位：像素 (例如 40x40 的实心正方形)
ANCHOR_COLOR_WHITE = (255, 255, 255) # 白色
ANCHOR_COLOR_BLACK = (0, 0, 0)       # 黑色
# 锚点位置 (例如，左上角)
ANCHOR_TOP_LEFT_X = 0
ANCHOR_TOP_LEFT_Y = 0
ANCHOR_BOTTOM_RIGHT_X = ANCHOR_TOP_LEFT_X + ANCHOR_SIZE_PX
ANCHOR_BOTTOM_RIGHT_Y = ANCHOR_TOP_LEFT_Y + ANCHOR_SIZE_PX

def is_point_in_anchor(x: int, y: int, anchor_x: int, anchor_y: int, size: int) -> bool:
    """
    [做什么] 判断一个像素坐标 (x, y) 是否在一个矩形锚点内部。
    [参数] 
        x, y: 待判断的像素坐标。
        anchor_x, anchor_y: 锚点左上角的坐标。
        size: 锚点的边长。
    [返回] True if inside, False otherwise.
    [用途] 接收端可以用这个函数快速判断某个检测到的亮点/暗点是不是定位锚点。
    """
    return (
        anchor_x <= x < anchor_x + size and
        anchor_y <= y < anchor_y + size
    )

# --- 锚点判断函数测试 ---
test_point_inside = (10, 10)
test_point_outside = (50, 50)
print(f"\n--- 锚点判断函数测试 ---")
print(f"锚点位置: ({ANCHOR_TOP_LEFT_X}, {ANCHOR_TOP_LEFT_Y}) -> ({ANCHOR_BOTTOM_RIGHT_X}, {ANCHOR_BOTTOM_RIGHT_Y})")
print(f"点 {test_point_inside} 在锚点内: {is_point_in_anchor(*test_point_inside, ANCHOR_TOP_LEFT_X, ANCHOR_TOP_LEFT_Y, ANCHOR_SIZE_PX)}")
print(f"点 {test_point_outside} 在锚点内: {is_point_in_anchor(*test_point_outside, ANCHOR_TOP_LEFT_X, ANCHOR_TOP_LEFT_Y, ANCHOR_SIZE_PX)}")