class OpticalProtocol:
    # --- 1. 物理显示参数 ---
    # 调整BLOCK_SIZE为10px，保持DATA_AREA_SIZE为1000（1000/10=100）
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
    THRESHOLD = 128

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
        
        # 可用格子数（非锚点区）
        available_cells = total_cells - anchor_cells  # 6800
        
        # 这里的 overhead 必须包含所有非数据位（协议头 + CRC）
        overhead = cls.SYNC_BITS + cls.SEQ_BITS + cls.LEN_BITS + cls.CRC_BITS # 56
        
        # 数据容量 = 可用格子数 - 协议开销
        # 注意：这里返回的是纯数据容量，不包括协议头和CRC
        data_capacity = available_cells - overhead  # 6800 - 56 = 6744 bits
        
        # 验证：确保协议头 + 数据 + CRC 的总长度不超过可用格子数
        total_bits = len(cls.SYNC_PATTERN) + cls.SEQ_BITS + cls.LEN_BITS + data_capacity + cls.CRC_BITS
        if total_bits > available_cells:
            # 调整数据容量，确保总长度不超过可用格子数
            data_capacity = available_cells - (len(cls.SYNC_PATTERN) + cls.SEQ_BITS + cls.LEN_BITS + cls.CRC_BITS)
            print(f"调整数据容量为: {data_capacity} bits")
        
        return data_capacity
    
    @classmethod
    def get_available_cells(cls):
        """
        获取可用格子数（非锚点区）
        """
        total_cells = cls.ROWS * cls.COLS  # 7056
        anchor_cells = (cls.ANCHOR_RESERVE ** 2) * 4  # 256
        return total_cells - anchor_cells  # 6800

    @classmethod
    def is_in_anchor_zone(cls, r, c):
        """判断坐标 (r, c) 是否属于四个角落的 8x8 预留区"""
        res = cls.ANCHOR_RESERVE
        is_top = r < res
        is_bottom = r >= (cls.ROWS - res)
        is_left = c < res
        is_right = c >= (cls.COLS - res)
        
        return (is_top or is_bottom) and (is_left or is_right)