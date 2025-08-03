import cv2
import numpy as np
from _shared_utils import write_log

class VisionUISystem:
    def __init__(self):
        write_log("VisionUISystem 初始化。")
        self.control_window_name = 'Vision Parameters'
        
        # 硬編碼的預設閾值
        self._hardcoded_default_black_stone_thresh = 50
        self._hardcoded_default_white_stone_thresh = 180
        
        # 初始化閾值
        self.black_stone_thresh = self._hardcoded_default_black_stone_thresh
        self.white_stone_thresh = self._hardcoded_default_white_stone_thresh
        
        # 創建 UI
        self._create_parameter_trackbars()

    def _create_parameter_trackbars(self):
        """創建用於調整影像處理參數的滑桿 UI。"""
        try:
            cv2.namedWindow(self.control_window_name, cv2.WINDOW_NORMAL)
            # 創建 200x600 的空白圖像作為視窗背景
            control_window_img = np.zeros((200, 600, 3), dtype=np.uint8)
            # 添加提示文字
            cv2.putText(control_window_img, "Adjust Thresholds", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.imshow(self.control_window_name, control_window_img)
            # 設定視窗置頂
            cv2.setWindowProperty(self.control_window_name, cv2.WND_PROP_TOPMOST, 1)

            # 創建滑桿
            cv2.createTrackbar('Black Thresh', self.control_window_name, self.black_stone_thresh, 255, self._on_black_stone_thresh_change)
            cv2.createTrackbar('White Thresh', self.control_window_name, self.white_stone_thresh, 255, self._on_white_stone_thresh_change)
            cv2.createTrackbar('Clear Points', self.control_window_name, 0, 1, self._on_clear_points)
            cv2.createTrackbar('--- Reset All ---', self.control_window_name, 0, 1, self._on_reset_button_press)
            cv2.createTrackbar('--- Save ---', self.control_window_name, 0, 1, self._on_save_button_press)

            write_log(f"視覺參數調整 UI 已創建，初始黑子閾值: {self.black_stone_thresh}, 白子閾值: {self.white_stone_thresh}")
        except Exception as e:
            write_log(f"創建視覺參數 UI 時發生錯誤: {e}")

    def _on_black_stone_thresh_change(self, val):
        self.black_stone_thresh = val
        write_log(f"黑子閾值更新為: {self.black_stone_thresh}")

    def _on_white_stone_thresh_change(self, val):
        self.white_stone_thresh = val
        if self.white_stone_thresh <= self.black_stone_thresh:
            self.white_stone_thresh = self.black_stone_thresh + 1
            if self.white_stone_thresh > 255:
                self.white_stone_thresh = 255
            cv2.setTrackbarPos('White Thresh', self.control_window_name, self.white_stone_thresh)
        write_log(f"白子閾值更新為: {self.white_stone_thresh}")

    def _on_clear_points(self, val):
        if val == 1:
            write_log("清除點按鈕被觸發。")
            cv2.setTrackbarPos('Clear Points', self.control_window_name, 0)

    def _on_reset_button_press(self, val):
        if val == 1:
            write_log("重置按鈕被觸發。")
            self.black_stone_thresh = self._hardcoded_default_black_stone_thresh
            self.white_stone_thresh = self._hardcoded_default_white_stone_thresh
            cv2.setTrackbarPos('Black Thresh', self.control_window_name, self.black_stone_thresh)
            cv2.setTrackbarPos('White Thresh', self.control_window_name, self.white_stone_thresh)
            cv2.setTrackbarPos('--- Reset All ---', self.control_window_name, 0)
            write_log(f"重置後黑子閾值: {self.black_stone_thresh}, 白子閾值: {self.white_stone_thresh}")

    def _on_save_button_press(self, val):
        if val == 1:
            write_log("保存按鈕被觸發。")
            cv2.setTrackbarPos('--- Save ---', self.control_window_name, 0)

    def run(self):
        """運行 UI 測試主迴圈。"""
        write_log("✅ VisionUISystem 測試模式已啟動。按 'q' 鍵退出。")
        while True:
            # 更新控制視窗
            try:
                control_window_img = np.zeros((200, 600, 3), dtype=np.uint8)
                cv2.putText(control_window_img, f"Black: {self.black_stone_thresh}, White: {self.white_stone_thresh}", 
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.imshow(self.control_window_name, control_window_img)
            except Exception as e:
                write_log(f"更新控制視窗時發生錯誤: {e}")
                break

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                write_log("用戶手動退出 VisionUISystem 測試。")
                break

    def cleanup(self):
        """清理資源並關閉視窗。"""
        cv2.destroyAllWindows()
        write_log("VisionUISystem 測試程式結束。")

if __name__ == "__main__":
    try:
        ui_system = VisionUISystem()
        ui_system.run()
    except Exception as e:
        write_log(f"🚨 VisionUISystem 測試發生錯誤: {e}")
    finally:
        ui_system.cleanup()