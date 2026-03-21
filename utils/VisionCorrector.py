import cv2
import numpy as np
from core.protocol import OpticalProtocol as P

class VisionCorrector:
    def __init__(self, target_size=(1008, 1008)):
        self.p = P()  # 实例化协议，获取 DRAW_ANCHOR_SIZE 等参数
        self.target_size = target_size
        # --- 核心修复：计算中心点偏移 ---
        # 锚点绘制大小是 DRAW_ANCHOR_SIZE，中心点就在一半的位置
        anchor_offset = self.p.DRAW_ANCHOR_SIZE // 2 + 8
        w, h = target_size
        
        # 我们让识别到的“中心点”映射到画布上“应该在的中心位置”
        # 这样锚点就不会被切掉，数据区也会自动归位
        self.dst_points = np.float32([
            [anchor_offset, anchor_offset],           # 左上中心
            [w - anchor_offset, anchor_offset],       # 右上中心
            [w - anchor_offset, h - anchor_offset],   # 右下中心
            [anchor_offset, h - anchor_offset]        # 左下中心
        ])
        self.last_frame_hash = None

    def _find_anchor_centers(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. 二值化：寻找白色区域
        _, thresh = cv2.threshold(gray, self.p.THRESHOLD, 255, cv2.THRESH_BINARY)
        
        # 使用 RETR_TREE 获取完整的轮廓嵌套层级 (Hierarchy)
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if hierarchy is None:
            return None
        
        hier = hierarchy[0]
        ideal_area = self.p.DRAW_ANCHOR_SIZE ** 2 
        candidates = []
        
        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            
            # --- 过滤逻辑 1：面积匹配 ---
            # 原片非常精准，给予 15% 的容错空间
            if not (ideal_area * 0.85 < area < ideal_area * 1.15):
                continue
            
            # --- 过滤逻辑 2：外接矩形比例 ---
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            if not (0.9 < aspect_ratio < 1.1):
                continue
            
            # --- 过滤逻辑 3：层级结构（核心改动） ---
            # 数据块是实心的，没有子轮廓。锚点有内部黑框，因此必有子轮廓。
            # hier[i][2] != -1 表示该轮廓拥有至少一个子轮廓
            if hier[i][2] != -1:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    candidates.append([cx, cy])

        # 2. 数量校验：必须找齐或超过 4 个点
        if len(candidates) < 4:
            return None
            
        # 3. 几何排序：确保 src_points 与 dst_points 顺序一一对应
        pts = np.array(candidates, dtype="float32")
        rect = np.zeros((4, 2), dtype="float32")
        
        # 左上: x+y 最小 | 右下: x+y 最大
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # 右上: y-x 最小 (即 x大y小) | 左下: y-x 最大 (即 x小y大)
        diff = pts[:, 1] - pts[:, 0]
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect

    def correct(self, frame):
        # 视觉去重逻辑
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (32, 32))
        curr_hash = resized.mean()
        
        if self.last_frame_hash is not None:
            # 原片极其稳定，阈值设为 0.1 即可过滤掉完全重复的帧
            if abs(curr_hash - self.last_frame_hash) < 0.1:
                return "SKIP"
        self.last_frame_hash = curr_hash

        # 执行定位与拉直
        src_points = self._find_anchor_centers(frame)
        if src_points is None:
            return None
        
        M = cv2.getPerspectiveTransform(src_points, self.dst_points)
        return cv2.warpPerspective(frame, M, self.target_size)