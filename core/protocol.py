class OpticalProtocol:
    # --- 1. 物理显示与采集参数 ---
    SCREEN_W = 1920 
    SCREEN_H = 1080 
    FPS = 15 

    BLOCK_SIZE = 18 
    ANCHOR_SIZE = 144 
    DRAW_ANCHOR_SIZE = 120
    
    ANCHOR_COLOR = 255 
    THRESHOLD = 127 

    # 数据区 1008x1008
    DATA_AREA_SIZE = 1008
    OFFSET_X = (SCREEN_W - DATA_AREA_SIZE) // 2  # 456
    OFFSET_Y = (SCREEN_H - DATA_AREA_SIZE) // 2  # 36

    COLS = DATA_AREA_SIZE // BLOCK_SIZE # 56
    ROWS = DATA_AREA_SIZE // BLOCK_SIZE # 56
    TOTAL_BLOCKS = COLS * ROWS          # 3136 格

    # --- 2. 帧结构定义 (保险逻辑核心) ---
    # 定义帧头各字段占用的比特数 (1 bit = 1 block)
    SYNC_BITS = 16    # 同步码：用于定位帧起始，过滤环境杂色
    SEQ_BITS = 8      # 帧序号：解决重复帧与丢帧 (0-255 循环)
    LEN_BITS = 16     # 载荷长度：标识本帧实际有效比特数
    CRC_BITS = 16     # CRC 校验：确保整帧数据无误

    # 同步码常量 (选一个抗噪强的比特序列，如 0xAAAA 或 0b1010...)
    SYNC_PATTERN = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]

    # --- 3. 辅助计算方法 ---
    @staticmethod
    def get_data_capacity_per_frame():
        """
        计算每帧真正能放多少 bits 的原始数据：
        总格数(3136) 
        - 锚点占位(8*8*4 = 256) 
        - 帧头(16+8+16 = 40) 
        - 帧尾校验(16)
        = 2824 bits (约 353 字节)
        """
        anchor_blocks = (OpticalProtocol.ANCHOR_SIZE // OpticalProtocol.BLOCK_SIZE) ** 2 * 4
        header_blocks = OpticalProtocol.SYNC_BITS + OpticalProtocol.SEQ_BITS + OpticalProtocol.LEN_BITS
        trailer_blocks = OpticalProtocol.CRC_BITS
        return OpticalProtocol.TOTAL_BLOCKS - anchor_blocks - header_blocks - trailer_blocks

    @staticmethod
    def is_in_anchor_zone(row, col):
        num_blocks = OpticalProtocol.ANCHOR_SIZE // OpticalProtocol.BLOCK_SIZE
        # 四个角返回 True
        if (row < num_blocks or row >= OpticalProtocol.ROWS - num_blocks) and \
           (col < num_blocks or col >= OpticalProtocol.COLS - num_blocks):
            return True
        return False

    @staticmethod
    def get_block_rect(row, col):
        x1 = OpticalProtocol.OFFSET_X + col * OpticalProtocol.BLOCK_SIZE
        y1 = OpticalProtocol.OFFSET_Y + row * OpticalProtocol.BLOCK_SIZE
        return x1, y1, x1 + OpticalProtocol.BLOCK_SIZE, y1 + OpticalProtocol.BLOCK_SIZE