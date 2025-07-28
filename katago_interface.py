import subprocess
import os
import time
import select


class KataGoGTP:
    """
    用於與 KataGo 圍棋引擎進行 GTP 協定通訊的類別。
    """

    def __init__(self, katago_path=None, model_path=None, config_path=None):
        self.katago_path = katago_path or os.getenv("KATAGO_PATH", self._find_katago_path())
        self.model_path = model_path or os.getenv("KATAGO_MODEL_PATH", "/opt/homebrew/Cellar/katago/1.16.3/share/katago/kata1-b28c512nbt-s9584861952-d4960414494.bin.gz")
        self.config_path = config_path or os.getenv("KATAGO_CONFIG_PATH", "/opt/homebrew/Cellar/katago/1.16.3/share/katago/configs/gtp_example.cfg")
        self.process = None

        # 檢查檔案是否存在
        for path, name in [(self.katago_path, "KataGo 可執行檔"), (self.model_path, "模型檔案"), (self.config_path, "配置文件")]:
            if not os.path.exists(path):
                print(f"錯誤：{name} 不存在於: {path}")
                raise FileNotFoundError(f"{name} 找不到: {path}")

    def _find_katago_path(self):
        """動態查找 KataGo 可執行檔路徑"""
        try:
            result = subprocess.run(['which', 'katago'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "/opt/homebrew/bin/katago"

    def start_katago(self):
        """
        啟動 KataGo 進程並延遲等待初始化（不再依賴 GTP ready 判斷）
        """
        command = [
            self.katago_path,
            "gtp",
            "-model", self.model_path,
            "-config", self.config_path
        ]
        print(f"啟動 KataGo 命令: {' '.join(command)}")
        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            print("KataGo 啟動成功，延遲 3 秒等待初始化...")
            time.sleep(3)  # 等待初始化完成（略過 GTP ready）
            print("KataGo 預估已準備就緒。")
        except Exception as e:
            print(f"啟動 KataGo 時發生錯誤: {e}")
            self.process = None
            raise

    def send_command(self, command):
        """
        向 KataGo 發送 GTP 指令並讀取其回覆。
        """
        if not self.process or self.process.poll() is not None:
            print("錯誤：KataGo 進程未啟動或已終止。")
            return None

        full_command = command.strip() + "\n"
        print(f"-> 發送指令: {full_command.strip()}")
        try:
            self.process.stdin.write(full_command)
            self.process.stdin.flush()
        except BrokenPipeError:
            print("錯誤：與 KataGo 進程的管道已斷開，KataGo 可能已崩潰。")
            return None

        response_lines = []
        timeout = 60
        while True:
            rlist, _, _ = select.select([self.process.stdout], [], [], timeout)
            if not rlist:
                print("錯誤：KataGo 回覆超時。")
                break
            if self.process.poll() is not None:
                print("KataGo 進程已結束。")
                break
            line = self.process.stdout.readline()
            if not line:
                print("KataGo 無輸出。")
                break
            response_lines.append(line.strip())
            print(f"<- 收到回覆: {line.strip()}")
            if line.strip() == "":
                break
        return "\n".join(response_lines)

    def parse_response(self, response):
        """
        解析 KataGo 的 GTP 回覆。
        返回一個字典，包含 'status' ('success', 'error', 'info') 和 'content'。
        """
        if not response:
            return {"status": "error", "content": "無 KataGo 回覆"}

        lines = response.split('\n')
        for line in lines:
            if line.startswith('='):
                return {"status": "success", "content": line[1:].strip()}
            elif line.startswith('?'):
                return {"status": "error", "content": line[1:].strip()}
        return {"status": "info", "content": response.strip()}

    def stop_katago(self):
        """
        停止 KataGo 進程。
        """
        if self.process and self.process.poll() is None:
            print("停止 KataGo 進程...")
            try:
                self.send_command("quit")
                self.process.wait(timeout=5)
            except Exception as e:
                print(f"發送 quit 指令時發生錯誤: {e}")
                if self.process.poll() is None:
                    print("KataGo 未正常退出，嘗試強制終止...")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=1)
                    except:
                        self.process.kill()
                    print("KataGo 已強制終止。")
            print(f"KataGo 進程已停止，退出碼: {self.process.returncode}")
        else:
            print("KataGo 進程已終止或未啟動。")


if __name__ == "__main__":
    katago_client = None
    try:
        katago_client = KataGoGTP()
        katago_client.start_katago()

        # 設定棋盤和貼目
        katago_client.send_command("boardsize 19") # 設定棋盤大小，你可以改為 9x9 或 13x13 方便測試
        katago_client.send_command("clear_board")
        katago_client.send_command("komi 6.5")

        print("\nKataGo 介面已準備就緒，您可以輸入 GTP 指令了。")
        print("例如：")
        print("  play B C4   (讓黑棋下在 C4)")
        print("  genmove W   (讓 KataGo 幫白棋生成一步棋)")
        print("  showboard   (顯示當前棋盤狀態)")
        print("  quit        (退出 KataGo 引擎並結束程式)")
        print("  name        (查詢引擎名稱)")
        print("  version     (查詢引擎版本)")
        
        while True:
            # 讓使用者輸入 GTP 指令
            user_input = input("\n請輸入 GTP 指令 (或 'quit' 退出): ").strip()

            if not user_input: # 如果輸入為空，繼續等待輸入
                continue

            if user_input.lower() == "quit":
                print("收到 'quit' 指令，正在結束程式...")
                break # 跳出迴圈，進入 finally 區塊停止 KataGo

            # 將使用者輸入的指令發送給 KataGo
            response = katago_client.send_command(user_input)
            
            # 解析並打印 KataGo 的回應
            parsed = katago_client.parse_response(response)
            if parsed['status'] == 'success':
                print(f"KataGo 回應: {parsed['content']}")
            elif parsed['status'] == 'error':
                print(f"KataGo 錯誤: {parsed['content']}")
            else: # info 狀態
                print(f"KataGo 訊息: {parsed['content']}")

    except Exception as e:
        print(f"\n程序執行中發生錯誤: {e}")
    finally:
        # 確保在程式結束時關閉 KataGo 進程
        if katago_client:
            katago_client.stop_katago()