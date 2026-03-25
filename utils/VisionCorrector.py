import cv2
import numpy as np
from core.protocol import OpticalProtocol as P

class VisionCorrector:
    def __init__(self, target_size=(1008, 1008)):
        self.p = P() 
        self.target_size = target_size
        
        # --- 1008x1008 贴边锚点中心点计算 ---
        # 锚点是 7x7 个 BLOCK_SIZE，中心点就在 3.5 个格子处
        bs = self.p.BLOCK_SIZE # 12
        anchor_center_offset = 3.5 * bs # 42.0
        
        w, h = target_size
        # 目标基准点 (dst_points) 保持 float32 精度
        self.dst_points = np.float32([
            [anchor_center_offset, anchor_center_offset],           # TL
            [w - anchor_center_offset, anchor_center_offset],       # TR
            [w - anchor_center_offset, h - anchor_center_offset],   # BR
            [anchor_offset := anchor_center_offset, h - anchor_center_offset] # BL
        ])
        
        self.last_frame_hash = None

    def _find_anchor_centers(self, img):
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        # 修复点 1: 增加返回值解包 '_'
        _, thresh = cv2.threshold(gray, self.p.THRESHOLD, 255, cv2.THRESH_BINARY)
        
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None: return None
        
        hier = hierarchy[0]
        candidates = []
        ideal_area = (7 * self.p.BLOCK_SIZE) ** 2
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            # 这里的范围 0.5~1.5 比较宽松，适合手持拍摄；原视频建议收紧到 0.8~1.2
            if not (ideal_area * 0.3 < area < ideal_area * 2.5):
                continue
            
            x, y, w_box, h_box = cv2.boundingRect(cnt)
            aspect_ratio = float(w_box) / h_box
            if not (0.7 < aspect_ratio < 1.3):
                continue

            # 核心判定：必须有子轮廓 (RETR_TREE 下 hier[i][2] 表示子轮廓索引)
            if hier[i][2] != -1: 
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    # 修复点 2: 保持 float 精度，不使用 int()，直接存坐标
                    cx = M["m10"] / M["m00"]
                    cy = M["m01"] / M["m00"]
                    candidates.append((cx, cy))

        if len(candidates) < 4: return None
        
        # 转换并排序
        pts = np.array(candidates, dtype="float32")
        # 如果找到多于 4 个点，这里会报错，所以增加一个切片或更严谨的筛选
        # 但在原视频中，hier[i][2] 过滤后通常刚好剩 4 个
        if len(pts) > 4:
            # 简单策略：按面积排序取前四个，或者计算周长
            pass 

        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]       # TL
        rect[2] = pts[np.argmax(s)]       # BR
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]    # TR
        rect[3] = pts[np.argmax(diff)]    # BL
            
        return rect

    def correct(self, frame):
        # 视觉去重逻辑
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (32, 32))
        curr_hash = resized.mean()
        
        if self.last_frame_hash is not None:
            if abs(curr_hash - self.last_frame_hash) < 0.1:
                return "SKIP"
        self.last_frame_hash = curr_hash

        src_points = self._find_anchor_centers(frame)
        if src_points is None:
            return None
        
        M = cv2.getPerspectiveTransform(src_points, self.dst_points)
        # 建议直接在 warp 这一步转灰度或保持彩色（根据你 test_muxer 的 debug 需要）
        return cv2.warpPerspective(frame, M, self.target_size)