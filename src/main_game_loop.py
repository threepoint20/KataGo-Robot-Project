# main_game_loop.py
import sys
import time
import cv2 # 為了 cv2.waitKey 和 cv2.destroyAllWindows
from _shared_utils import write_log # 從共用工具導入日誌功能
from katago_gtp import KataGoGTP # 導入 KataGoGTP 類別
from robot_controller import RobotArmController, gtp_to_robot_coords # 導入機械臂控制器和座標轉換函數
from vision_system import VisionSystem # 導入視覺系統

# --- 遊戲主循環 ---
if __name__ == "__main__":
    katago_client = None
    robot_controller = None
    vision_system = None
    
    # 追蹤當前輪到哪方下子，B = 黑棋，W = 白棋
    current_player = "B" 
    
    # 棋局狀態追蹤
    game_over = False
    turn_count = 0
    consecutive_passes = 0 # 追蹤連續 pass 的次數，兩個 pass 則遊戲結束

    # 模擬棋盤的內部狀態，將來會由視覺系統更新
    board_state = {} 

    try:
        katago_client = KataGoGTP(
            # 如果需要，在這裡設定您的 KataGo 路徑，例如:
            # katago_path="/Users/suying-chu/Downloads/katago/KataGo-mac-arm64/katago",
            # model_path="/Users/suying-chu/Downloads/katago/KataGo-mac-arm64/models/kata100.bin.gz",
            # config_path="/Users/suying-chu/Downloads/katago/KataGo-mac-arm64/gtp_config.cfg"
        )
        
        # 初始化機械臂和視覺系統
        robot_controller = RobotArmController() # 實例化機械臂控制器
        vision_system = VisionSystem() # 實例化視覺系統
        
        # --- 啟動所有系統 ---
        if not katago_client.start_katago():
            write_log("KataGo 啟動失敗，程式終止。")
            sys.exit(1) # 使用 sys.exit 確保退出

        robot_controller.connect() # 連接機械臂
        if not vision_system.start_camera(): # 啟動相機
            write_log("視覺系統相機啟動失敗，程式終止。")
            sys.exit(1) # 使用 sys.exit 確保退出

        write_log("\n✅ 圍棋機械人系統準備就緒。")
        write_log("遊戲開始！")
        
        # 初始化 KataGo 的棋盤狀態
        katago_client.send_command("boardsize 19")
        katago_client.send_command("clear_board")
        robot_controller.reset_board() # 物理清空棋盤 (模擬)
        
        # 初始獲取一次棋盤狀態，確保視覺系統就緒 (即使是空的)
        board_state = vision_system.get_board_state()

        while not game_over:
            turn_count += 1
            write_log(f"\n--- 第 {turn_count} 回合：輪到 {current_player} 下子 ---")

            if current_player == "B": # 人類玩家（黑棋）回合
                # 視覺系統偵測人類落子 (目前依賴 input() 模擬)
                human_move_action = None
                # 持續從視覺系統獲取輸入，直到有效或退出
                while human_move_action is None:
                    # 傳入當前的棋盤狀態給視覺系統，未來用於比較辨識新落子
                    human_move_action = vision_system.detect_human_move(board_state, None) # None 應為實際的 current_board_state
                    
                    # 確保 OpenCV 視窗在等待人類輸入時也能響應
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        write_log("用戶手動退出遊戲。")
                        game_over = True
                        break # 跳出內層循環

                    if human_move_action is None:
                        write_log("無效的人類輸入，請重新輸入。")
                        time.sleep(0.5) # 避免過快循環打印錯誤

                if game_over: # 如果用戶在等待輸入時退出了
                    break

                if human_move_action.lower() == "quit":
                    game_over = True
                    write_log("人類玩家選擇退出遊戲。")
                    break
                
                if human_move_action.lower().startswith("pass"): # human_move_action 是 "pass"
                    write_log(f"人類玩家（{current_player}）選擇 pass。")
                    # 通知 KataGo 人類 pass
                    katago_client.send_command(f"play {current_player} pass")
                    consecutive_passes += 1 # 增加連續 pass 計數
                    if consecutive_passes >= 2:
                        write_log("連續兩次 pass，遊戲結束。")
                        game_over = True
                    else:
                        current_player = "W" if current_player == "B" else "B" # 切換到白棋
                        write_log(f"✅ 回合切換：下一個輪到 {current_player} 下子。")
                else:
                    # 解析人類落子 "B D4" -> human_color='B', human_coord='D4'
                    human_color = human_move_action.split(' ')[0]
                    human_coord = human_move_action.split(' ')[1]

                    write_log(f"偵測到人類落子：{human_color} {human_coord}")
                    
                    # 通知 KataGo 人類已落子
                    play_cmd = f"play {human_color} {human_coord}"
                    raw_response = katago_client.send_command(play_cmd)
                    parsed_response = katago_client.parse_response(raw_response)

                    if parsed_response['status'] == 'success':
                        write_log(f"✅ KataGo 內部棋盤已更新。人類落子回應：{parsed_response['content']}")
                        consecutive_passes = 0 # 落子後，連續 pass 計數歸零
                        current_player = "W" if current_player == "B" else "B" # 切換到白棋
                        write_log(f"✅ 回合切換：下一個輪到 {current_player} 下子。")
                    elif parsed_response['status'] == 'error':
                        write_log(f"❌ KataGo 內部棋盤更新失敗：{parsed_response['content']}。人類落子可能無效。")
                        # 這裡可能需要機械臂撿起下錯的棋子，或請求人類重新下
                        turn_count -= 1 # 本回合不算，讓人類重下
                        # 不切換回合，等待人類修正
                    else:
                        write_log(f"ℹ️ KataGo 訊息：{parsed_response['content']}")
                        consecutive_passes = 0 # 收到回應（非錯誤）則歸零
                        current_player = "W" if current_player == "B" else "B" # 切換到白棋


            elif current_player == "W": # 機械臂 (KataGo) 回合
                write_log("請求 KataGo 思考白棋落子...")
                raw_response = katago_client.send_command(f"genmove {current_player}") 
                parsed_response = katago_client.parse_response(raw_response)

                if parsed_response['status'] == 'success':
                    katago_move = parsed_response['content'].strip()
                    write_log(f"✅ KataGo 建議落子：{katago_move}")

                    if katago_move.lower() == "pass":
                        write_log("KataGo 選擇 'pass'，不執行機械臂動作。")
                        # 通知 KataGo 機械臂 pass
                        katago_client.send_command(f"play {current_player} pass")
                        consecutive_passes += 1 # 增加連續 pass 計數
                        if consecutive_passes >= 2:
                            write_log("連續兩次 pass，遊戲結束。")
                            game_over = True
                        else:
                            current_player = "B" if current_player == "W" else "W" # 切換到黑棋
                            write_log(f"✅ 回合切換：下一個輪到 {current_player} 下子。")
                    else:
                        # 將 KataGo 的落子位置轉換為機械臂座標
                        robot_target_xy = gtp_to_robot_coords(katago_move)

                        if robot_target_xy:
                            robot_x, robot_y = robot_target_xy
                            write_log(f"機械臂將移動到: X={robot_x:.2f}mm, Y={robot_y:.2f}mm。")
                            
                            # --- 呼叫實際的機械臂控制程式碼 ---
                            robot_controller.pick_stone(current_player) # 吸取當前回合顏色的棋子
                            robot_controller.place_stone(robot_x, robot_y) # 放置棋子
                            # robot_controller.retract() # 回到安全位置，如果 place_stone 裡面沒有包含的話

                            # 重要：通知 KataGo 機械臂已落子 (更新 KataGo 的內部棋局狀態)
                            play_command_for_katago = f"play {current_player} {katago_move}" 
                            katago_client.send_command(play_command_for_katago)
                            write_log(f"已通知 KataGo 執行落子: {play_command_for_katago}")
                            
                            consecutive_passes = 0 # 落子後，連續 pass 計數歸零
                            current_player = "B" if current_player == "W" else "W" # 切換到黑棋
                            write_log(f"✅ 回合切換：下一個輪到 {current_player} 下子。")
                        else:
                            write_log("無法轉換落子座標，不執行機械臂動作。")
                            # 這表示程式邏輯錯誤，可能需要停止遊戲或人工干預
                            game_over = True # 暫時設定遊戲結束
                elif parsed_response['status'] == 'error':
                    write_log(f"❌ KataGo 錯誤：{parsed_response['content']}")
                    game_over = True # KataGo 錯誤通常意味著遊戲無法繼續
                else:
                    write_log(f"ℹ️ KataGo 訊息：{parsed_response['content']}")
                    consecutive_passes = 0 # 收到回應（非錯誤）則歸零
                    current_player = "B" if current_player == "W" else "W" # 切換到黑棋
            
            # 判斷遊戲結束條件 (簡化範例)
            # 例如：達到最大回合數
            # if turn_count >= 100: game_over = True # 設置最大回合數

    except FileNotFoundError as e:
        write_log(f"\n🚨 檔案找不到錯誤：{e}")
    except Exception as e:
        write_log(f"\n🚨 發生未預期的錯誤：{e}")
    finally:
        write_log("\n--- 遊戲結束，清理資源 ---")
        if katago_client:
            katago_client.stop_katago()
        if robot_controller:
            robot_controller.disconnect()
        if vision_system:
            vision_system.stop_camera()
        write_log("程式執行結束。")