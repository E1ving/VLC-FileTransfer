class OpticalProtocol:
    # --- 1. 物理显示参数 ---
    DATA_AREA_SIZE = 1000
    SCREEN_W = 1000
    SCREEN_H = 1000
    
    BLOCK_SIZE = 10 
    ANCHOR_RESERVE = 8  # 8x8 预留区 (包含白边隔离带)

    # 1000 / 10 = 100
    COLS = 100
    ROWS = 100

    # --- 2. 帧结构定义 (单位: Bits) ---
    SYNC_BITS = 16    
    SEQ_BITS = 8      
    LEN_BITS = 16     
    CRC_BITS = 16     
    
    # 同步码模式
    SYNC_PATTERN = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]

    # 视觉处理阈值
    THRESHOLD = 127

    @classmethod
    def get_header_bits_count(cls):
        """同步码 + 序列号 + 长度字段"""
        return cls.SYNC_BITS + cls.SEQ_BITS + cls.LEN_BITS

    @classmethod
    def get_data_capacity_per_frame(cls):
        """
        计算每一帧能够承载的【纯数据】比特数
        计算公式：总格子数 - 4个锚点区 - 协议头 - CRC校验位
        """
        total_cells = cls.ROWS * cls.COLS  # 7056
        anchor_cells = (cls.ANCHOR_RESERVE ** 2) * 4  # 256
        
        # 这里的 overhead 必须包含所有非数据位
        overhead = cls.SYNC_BITS + cls.SEQ_BITS + cls.LEN_BITS + cls.CRC_BITS # 56
        
        return total_cells - anchor_cells - overhead # 7056 - 256 - 56 = 6744 bits

    @classmethod
    def is_in_anchor_zone(cls, r, c):
        """判断坐标 (r, c) 是否属于四个角落的 8x8 预留区"""
        res = cls.ANCHOR_RESERVE
        is_top = r < res
        is_bottom = r >= (cls.ROWS - res)
        is_left = c < res
        is_right = c >= (cls.COLS - res)
        
        return (is_top or is_bottom) and (is_left or is_right)