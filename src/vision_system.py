# vision_system.py
import cv2
import time
from _shared_utils import write_log # 從共用工具導入日誌功能

class VisionSystem:
    def __init__(self):
        write_log("VisionSystem 初始化 (模擬)。")
        self.cap = None # OpenCV VideoCapture 物件
        self.camera_index = 0 # 根據您之前的偵錯，Camo Camera 是索引 0

    def start_camera(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        if not self.cap.isOpened():
            write_log(f"錯誤：視覺系統無法打開攝影機索引 {self.camera_index}。")
            return False
        write_log(f"視覺系統成功連接到攝影機索引 {self.camera_index}。")
        return True

    def get_board_state(self):
        """
        模擬從相機獲取棋盤狀態並返回一個字典。
        實際應包含棋盤上所有黑白子的位置。
        """
        ret, frame = self.cap.read()
        if not ret:
            write_log("視覺系統：無法從攝影機讀取影像。")
            return None
        
        # ================================================
        # 在這裡進行您的電腦視覺處理 (棋盤偵測、棋子偵測等)
        # 這部分是您接下來將要實現的核心功能
        # ================================================
        
        # 範例：顯示即時畫面 (可以添加處理步驟後的影像顯示)
        # 轉換為灰度影像
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # 高斯模糊
        blurred_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)
        # Canny 邊緣檢測
        edges = cv2.Canny(blurred_frame, 100, 200)
        
        # 顯示處理後的影像
        cv2.imshow('Live Camera Feed (Vision System - Original)', frame)
        cv2.imshow('Live Camera Feed (Vision System - Edges)', edges)


        # 這裡應實現棋盤和棋子辨識，返回當前棋盤上所有棋子的位置
        # 例如：{"B": ["D4", "Q16"], "W": ["K10"]}
        write_log("視覺系統模擬：獲取當前棋盤狀態。")
        
        # 模擬返回一個空的棋盤狀態，或根據需要模擬一些棋子
        # 實際應根據視覺辨識結果返回真實的棋盤狀態
        return {} 

    def detect_human_move(self, prev_board_state, current_board_state):
        """
        模擬偵測人類的新落子，返回 GTP 座標和顏色 (例如 "B D4")。
        在實際整合視覺系統後，這部分將完全由視覺辨識結果替換。
        """
        write_log("等待人類玩家落子... (請在程式外部的物理棋盤上落子)")
        
        # --- 模擬人類通過輸入來“落子”，未來這將是視覺辨識的輸出 ---
        human_move_input = input("請輸入人類落子 (例如 B D4, 或 'pass'/'quit'): ").strip()
        if human_move_input.lower() == "quit":
            return "quit"
        if human_move_input.lower() == "pass":
            # 這裡簡單返回 "pass"，顏色會在主邏輯中根據 current_player 判斷
            return "pass" 
        
        parts = human_move_input.split(' ')
        if len(parts) == 2 and parts[0].upper() in ["B", "W"]:
            color = parts[0].upper()
            coord = parts[1].upper()
            write_log(f"視覺系統模擬：偵測到人類落子：{color} {coord}")
            return f"{color} {coord}"
        else:
            write_log("視覺系統模擬：人類輸入格式不正確，請重新輸入。")
            return None 

    def stop_camera(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        write_log("視覺系統攝影機已停止。")