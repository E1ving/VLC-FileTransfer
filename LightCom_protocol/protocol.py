class OpticalProtocol:
    # 基于拍摄设备支持1080P 60FPS输出，设计如下物理参数
    SCREEN_W = 1920 # 屏幕宽度
    SCREEN_H = 1080 # 屏幕高度
    FPS = 60 # 帧率(暂定)

    BLOCK_SIZE = 18 # 每个0/1方块的大小
    
    ANCHOR_SIZE = 108 # 定位块大小
    ANCHOR_COLOR= 255 # 定位块颜色

    THRESHOLD = 127 # 信号处理参数：灰度图的取值范围是 0-255
    
    # 我们在 1920 宽度的中间取一个约 1008 像素宽的正方形数据区
    OFFSET_X = (SCREEN_W - 1008) // 2  # 456
    OFFSET_Y = (SCREEN_H - 1008) // 2  # 36

    COLS = 1008 // BLOCK_SIZE # 56列
    ROWS = 1008 // BLOCK_SIZE # 56行

    BITS_PER_FRAME = COLS * ROWS # 每帧3136bits(暂定)

    CRC_BITS = 16  # 预留 16 位做 CRC

    @staticmethod
    def get_block_rect(row, col):
        """发送端调用：计算格子的矩形坐标"""
        x1 = OpticalProtocol.OFFSET_X + col * OpticalProtocol.BLOCK_SIZE
        y1 = OpticalProtocol.OFFSET_Y + row * OpticalProtocol.BLOCK_SIZE
        x2 = x1 + OpticalProtocol.BLOCK_SIZE
        y2 = y1 + OpticalProtocol.BLOCK_SIZE
        return x1, y1, x2, y2

    @staticmethod
    def get_anchor_positions():
        """接收端调用：定义理想状态下四个定位符的中心坐标，用于透视变换"""
        # 返回四个角的坐标：左上, 右上, 右下, 左下
        ox = OpticalProtocol.OFFSET_X
        oy = OpticalProtocol.OFFSET_Y
        # 这里定义的是定位符“外边缘”的四个点
        side = OpticalProtocol.COLS * OpticalProtocol.BLOCK_SIZE
        return [
            [ox, oy],              # 左上
            [ox + side, oy],       # 右上
            [ox + side, oy + side],# 右下
            [ox, oy + side]        # 左下
        ]

    @staticmethod
    def is_in_anchor_zone(row, col):
        """
        判断当前的 (row, col) 格子是否落在四个角的定位块范围内。
        """
        # 计算定位块占了多少个格子
        num_blocks = OpticalProtocol.ANCHOR_SIZE // OpticalProtocol.BLOCK_SIZE # 108 / 18 = 6
        # 1. 左上角区域
        if row < num_blocks and col < num_blocks:
            return True
        # 2. 右上角区域
        if row < num_blocks and col >= (OpticalProtocol.COLS - num_blocks):
            return True
        # 3. 左下角区域
        if row >= (OpticalProtocol.ROWS - num_blocks) and col < num_blocks:
            return True
        # 4. 右下角区域
        if row >= (OpticalProtocol.ROWS - num_blocks) and col >= (OpticalProtocol.COLS - num_blocks):
            return True
            
        return False

    @staticmethod
    def get_data_capacity_per_frame():
        """
        总格数: 3136
        锚点占位: 6 * 6 * 4 = 144 格
        校验位: 16 格
        净载荷: 3136 - 144 - 16 = 2976 bits
        """
        return 2976
