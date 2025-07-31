# robot_controller.py
import time
from _shared_utils import write_log # 從共用工具導入日誌功能
import numpy as np # 用於數學運算，如 pi

# --- 圍棋盤和機械臂的物理參數 (請根據您的實際測量值來設定) ---
# 這些值是機械臂校準後確定的，請您精確測量！
# 圍棋盤每個格點中心的物理間距 (單位: 毫米)
CELL_SIZE_MM = 20.0 # 範例值，請替換為您實際測量的棋盤格點間距

# 棋盤上 'A1' 交叉點的機械臂物理座標 (單位: 毫米)
# 假設棋盤的 A1 點是機械臂的參考原點，X軸向右，Y軸向上。
# 請用您實際測量的值來替換這些範例值
ROBOT_BOARD_ORIGIN_X_MM = 150.0 # 'A1' 點的機械臂 X 座標
ROBOT_BOARD_ORIGIN_Y_MM = 100.0 # 'A1' 點的機械臂 Y 座標

# GTP 列字母到索引的映射 (跳過 'I')
GTP_COL_MAP = {
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7,
    'J': 8, 'K': 9, 'L': 10, 'M': 11, 'N': 12, 'O': 13, 'P': 14,
    'Q': 15, 'R': 16, 'S': 17, 'T': 18
}

def gtp_to_robot_coords(gtp_move):
    """
    將 GTP 座標 (例如 "D4", "Q16") 轉換為機械臂的物理 (X, Y) 座標。
    假設棋盤 A1 點是機械臂的參考原點，X軸向右，Y軸向上。

    Args:
        gtp_move (str): GTP 格式的落子座標，例如 "D4" 或 "Q16"。

    Returns:
        tuple: (robot_x_mm, robot_y_mm) 該位置在機械臂工作空間中的物理座標。
               如果輸入無效，返回 None。
    """
    gtp_move = gtp_move.strip().upper()

    if len(gtp_move) < 2 or len(gtp_move) > 3:
        write_log(f"錯誤: 無效的 GTP 座標格式: {gtp_move} (長度不符)")
        return None

    col_char = gtp_move[0]
    row_num_str = gtp_move[1:]

    if col_char not in GTP_COL_MAP:
        write_log(f"錯誤: 無效的 GTP 列字母: {col_char} (不在 A-T 範圍或為 I)")
        return None

    try:
        row_num = int(row_num_str)
        if not (1 <= row_num <= 19):
            write_log(f"錯誤: 無效的 GTP 行號: {row_num_str} (必須在 1-19 之間)")
            return None
    except ValueError:
        write_log(f"錯誤: GTP 行號格式錯誤: {row_num_str} (非數字)")
        return None

    # 將 GTP 字母轉換為 0-18 的列索引
    col_index = GTP_COL_MAP[col_char]
    
    # 將 GTP 行號轉換為 0-18 的行索引 (GTP 1 對應索引 0，GTP 19 對應索引 18)
    row_index = row_num - 1 

    # 計算機械臂的 X 座標
    # 從 A1 原點開始，向右移動 col_index * CELL_SIZE_MM
    robot_x_mm = ROBOT_BOARD_ORIGIN_X_MM + (col_index * CELL_SIZE_MM)

    # 計算機械臂的 Y 座標
    # 從 A1 原點開始，向上移動 row_index * CELL_SIZE_MM
    robot_y_mm = ROBOT_BOARD_ORIGIN_Y_MM + (row_index * CELL_SIZE_MM)

    write_log(f"GTP 座標 {gtp_move} (列索引: {col_index}, 行索引: {row_index}) 轉換為機械臂座標: (X={robot_x_mm:.2f}mm, Y={robot_y_mm:.2f}mm)")
    return (robot_x_mm, robot_y_mm)


class RobotArmController:
    def __init__(self):
        write_log("RobotArmController 初始化 (模擬)。")
        # Z 軸高度常數，您需要精確測量並替換這些值
        self.Z_SAFE_RETRACT = 50.0   # 安全高度 (例如，高於棋盤 50mm)
        self.Z_PLACEMENT = 2.0       # 放置棋子的高度 (例如，高於棋盤表面 2mm)
        self.Z_PICKUP_STONE = -95.0  # 吸取棋子的高度 (例如，相對於棋子盒底部 -95mm)

        # 棋子盒的 X, Y 座標 (這也需要校準)
        # 請替換為您實際測量的棋子盒座標
        self.X_BLACK_CONTAINER = 20.0 # 黑色棋子盒的 X 座標
        self.Y_BLACK_CONTAINER = 20.0 # 黑色棋子盒的 Y 座標
        self.X_WHITE_CONTAINER = 20.0 # 白色棋子盒的 X 座標
        self.Y_WHITE_CONTAINER = 40.0 # 白色棋子盒的 Y 座標

    def connect(self):
        write_log("機械臂連接成功 (模擬)。")
        time.sleep(1) # 模擬連接時間

    def disconnect(self):
        write_log("機械臂斷開連接 (模擬)。")
        time.sleep(0.5) # 模擬斷開時間

    def pick_stone(self, color):
        write_log(f"機械臂模擬：吸取 {color} 棋子。")
        if color.lower() == "black":
            container_x, container_y = self.X_BLACK_CONTAINER, self.Y_BLACK_CONTAINER
        else: # white
            container_x, container_y = self.X_WHITE_CONTAINER, self.Y_WHITE_CONTAINER

        # 這裡應該有機械臂移動到棋子盒，啟動夾具/吸盤，然後提起回到安全高度的實際指令
        self.move_to_position(container_x, container_y, self.Z_SAFE_RETRACT) # 先到安全高度
        self.move_to_position(container_x, container_y, self.Z_PICKUP_STONE) # 下降到吸取高度
        self.activate_gripper() # 激活夾具
        self.move_to_position(container_x, container_y, self.Z_SAFE_RETRACT) # 提起回到安全高度
        time.sleep(2) # 模擬吸取時間
        write_log(f"機械臂模擬：吸取 {color} 棋子完成。")

    def place_stone(self, robot_x, robot_y):
        write_log(f"機械臂模擬：放置棋子到 X={robot_x:.2f}mm, Y={robot_y:.2f}mm。")
        # 這裡應該有機械臂移動到棋盤上方安全高度，再下降到放置高度，釋放夾具/吸盤，然後提起的實際指令
        self.move_to_position(robot_x, robot_y, self.Z_SAFE_RETRACT) # 先到目標上方安全高度
        self.move_to_position(robot_x, robot_y, self.Z_PLACEMENT) # 下降到放置高度
        self.release_gripper() # 釋放夾具
        self.move_to_position(robot_x, robot_y, self.Z_SAFE_RETRACT) # 提起回到安全高度
        time.sleep(3) # 模擬放置時間
        write_log(f"機械臂模擬：放置棋子完成。")

    def move_to_position(self, x, y, z):
        # 這是底層的移動指令，您需要對接到您的機械臂 SDK
        # 例如：
        # your_robot_sdk_instance.move_to_cartesian(x, y, z)
        write_log(f"機械臂模擬：移動到 X:{x:.2f}, Y:{y:.2f}, Z:{z:.2f}")
        pass 

    def activate_gripper(self):
        write_log("機械臂模擬：夾具/吸盤激活。")
        # 實際控制夾具/吸盤的開合或真空泵
        pass

    def release_gripper(self):
        write_log("機械臂模擬：夾具/吸盤釋放。")
        # 實際控制夾具/吸盤的開合或真空泵
        pass

    def reset_board(self):
        write_log("機械臂模擬：清空棋盤 (物理操作)。")
        # 這裡可以加入機械臂掃過棋盤，將所有棋子移除的邏輯
        time.sleep(5) # 模擬清空時間
        write_log("機械臂模擬：清空棋盤完成。")