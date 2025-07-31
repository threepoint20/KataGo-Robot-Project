# katago_gtp.py
import subprocess
import os
import time
import select
import threading
import queue
from _shared_utils import write_log, LOG_FILE_PATH # 從共用工具導入日誌功能

class KataGoGTP:
    def __init__(self, katago_path=None, model_path=None, config_path=None):
        # 這裡不再清除日誌檔，由 _shared_utils.py 處理首次寫入時的清除

        self.katago_path = katago_path or os.getenv("KATAGO_PATH", self._find_katago_path())
        self.model_path = model_path or os.getenv("KATAGO_MODEL_PATH", "/opt/homebrew/Cellar/katago/1.16.3/share/katago/kata1-b28c512nbt-s9584861952-d4960414494.bin.gz")
        self.config_path = config_path or os.getenv("KATAGO_CONFIG_PATH", "/opt/homebrew/Cellar/katago/1.16.3/share/katago/configs/gtp_example.cfg")
        self.process = None
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.io_thread = None
        self._stop_io_thread = threading.Event()

        write_log("KataGoGTP 實例化。")

        for path, name in [(self.katago_path, "KataGo 可執行檔"), (self.model_path, "模型檔案"), (self.config_path, "配置文件")]:
            if not os.path.exists(path):
                write_log(f"錯誤: {name} 找不到: {path}")
                raise FileNotFoundError(f"{name} 找不到: {path}")
        write_log("所有 KataGo 相關檔案路徑檢查通過。")

    def _find_katago_path(self):
        try:
            result = subprocess.run(['which', 'katago'], capture_output=True, text=True)
            if result.returncode == 0:
                write_log(f"通過 'which katago' 找到 KataGo 路徑: {result.stdout.strip()}")
                return result.stdout.strip()
        except Exception as e:
            write_log(f"執行 'which katago' 失敗: {e}")
            pass
        default_path = "/opt/homebrew/Cellar/katago/1.16.3/bin/katago"
        write_log(f"未能自動找到 KataGo 路徑，使用預設路徑: {default_path}")
        return default_path

    def _read_io_thread(self):
        """在獨立線程中持續讀取 stdout 和 stderr 並放入佇列"""
        write_log("[IO Thread] I/O 讀取線程啟動。")
        while not self._stop_io_thread.is_set():
            if not self.process or self.process.poll() is not None:
                write_log("[IO Thread] KataGo 進程已終止，停止 I/O 線程。")
                break

            readable, _, _ = select.select([self.process.stdout, self.process.stderr], [], [], 0.05) 

            if self.process.stdout in readable:
                line = self.process.stdout.readline()
                if line:
                    stripped = line.strip()
                    self.stdout_queue.put(stripped)
                    write_log(f"[IO Thread] <- STDOUT: '{stripped}'")
                elif self.process.poll() is not None: 
                    write_log("[IO Thread] STDOUT 管道已關閉。")
                    self._stop_io_thread.set()
                    break

            if self.process.stderr in readable:
                line = self.process.stderr.readline()
                if line:
                    stripped = line.strip()
                    self.stderr_queue.put(stripped)
                    write_log(f"[IO Thread] <- STDERR: '{stripped}'")
        write_log("[IO Thread] I/O 讀取線程結束。")


    def start_katago(self):
        command = [self.katago_path, "gtp", "-model", self.model_path, "-config", self.config_path]
        write_log(f"啟動 KataGo 命令: {' '.join(command)}")
        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding='utf-8'
            )
            write_log("KataGo 進程啟動成功。")

            self._stop_io_thread.clear()
            self.io_thread = threading.Thread(target=self._read_io_thread, daemon=True)
            self.io_thread.start()
            write_log("I/O 讀取線程已啟動。")

            # 新的啟動等待邏輯 (靜默判斷)
            start_time = time.time()
            last_output_time = time.time()
            initial_output_collected = []
            write_log("等待 KataGo 初始化完成 (靜默判斷)...")
            
            while time.time() - start_time < 30: # 總共最多等待 30 秒
                has_output_this_loop = False

                # 檢查 stdout 佇列
                while not self.stdout_queue.empty():
                    try:
                        line = self.stdout_queue.get_nowait()
                        initial_output_collected.append(f"[STDOUT]: {line}")
                        write_log(f"[啟動時 STDOUT]: {line}")
                        last_output_time = time.time()
                        has_output_this_loop = True
                    except queue.Empty:
                        pass
                
                # 檢查 stderr 佇列
                while not self.stderr_queue.empty():
                    try:
                        line = self.stderr_queue.get_nowait()
                        initial_output_collected.append(f"[STDERR]: {line}")
                        write_log(f"[啟動時 STDERR]: {line}")
                        last_output_time = time.time()
                        has_output_this_loop = True
                    except queue.Empty:
                        pass
                
                # 判斷是否進入「靜默期」
                if time.time() - last_output_time > 5: # 如果超過 5 秒沒有新的輸出，則認為 KataGo 已啟動並準備就緒
                    write_log(f"檢測到 KataGo 已靜默 {time.time() - last_output_time:.2f} 秒。認為已啟動完成。")
                    return True

                time.sleep(0.1) # 短暫延遲，避免忙等待

            write_log(f"警告: KataGo 在 30 秒內未顯示啟動完成標誌。已收集的初始輸出:\n{os.linesep.join(initial_output_collected)}")
            return False

        except Exception as e:
            write_log(f"啟動失敗: {e}")
            self.process = None
            raise

    def send_command(self, command):
        if not self.process or self.process.poll() is not None:
            write_log("錯誤：KataGo 未啟動或已終止。")
            return None

        full_command = command.strip() + "\n"
        write_log(f"-> 發送指令: '{full_command.strip()}'")
        try:
            self.process.stdin.write(full_command)
            self.process.stdin.flush()
            write_log(f"指令 '{command.strip()}' 已成功發送到 KataGo stdin。")
        except Exception as e:
            write_log(f"錯誤寫入 stdin: {e}")
            return None

        # 清空佇列，準備接收新回應
        while not self.stdout_queue.empty():
            try:
                self.stdout_queue.get_nowait()
            except queue.Empty:
                break
        while not self.stderr_queue.empty():
            try:
                self.stderr_queue.get_nowait()
            except queue.Empty:
                break
        write_log("已清空 stdout/stderr 佇列，準備接收新回應。")

        response_lines = []
        is_genmove_like = command.strip().lower().startswith("genmove")
        timeout = 120 if is_genmove_like else 10
        start_time = time.time()
        move_from_stderr = None # 專門用於 genmove 的 stderr fallback
        response_started = False
        
        write_log(f"開始等待指令 '{command.strip()}' 的回應，超時設定為 {timeout} 秒。")

        while True:
            current_time = time.time()
            # 優先檢查超時
            if current_time - start_time > timeout:
                write_log(f"錯誤：KataGo 回覆超時 ({timeout}秒)。目前從佇列收到回應內容：\n{os.linesep.join(response_lines)}")
                # 超時時，如果已經開始接收回應，則返回已接收的內容，讓 parse_response 處理
                if response_started:
                    write_log("已開始接收回應，但在超時時未收到結束標誌，返回部分回應。")
                    return "\n".join(response_lines)
                
                # 如果是 genmove 且沒有收到 stdout 回應，檢查 stderr 佇列是否有結果
                if is_genmove_like and not response_lines:
                    temp_stderr_lines = []
                    while not self.stderr_queue.empty():
                        temp_stderr_lines.append(self.stderr_queue.get_nowait())
                    
                    for line in temp_stderr_lines:
                        if "= " in line:
                            try:
                                move = line.split("= ", 1)[1].split()[0]
                                if len(move) > 1 and 'A' <= move[0].upper() <= 'T' and move[1:].isdigit():
                                    write_log(f"在 STDERR 佇列中找到落子結果 (超時): {move}")
                                    return f"= {move}\n\n"
                            except Exception as e:
                                write_log(f"解析 STDERR 中的落子結果失敗 (超時): {e}")
                        write_log(f"[超時時 STDERR]: {line}")
                    for line in temp_stderr_lines:
                        self.stderr_queue.put(line)

                return None

            # 檢查 KataGo 進程是否已終止
            if self.process.poll() is not None:
                write_log("KataGo 進程已終止，停止等待回應。")
                if response_started:
                    return "\n".join(response_lines)

                if is_genmove_like and not response_lines:
                    temp_stderr_lines = []
                    while not self.stderr_queue.empty():
                        temp_stderr_lines.append(self.stderr_queue.get_nowait())
                    for line in temp_stderr_lines:
                        if "= " in line:
                            try:
                                move = line.split("= ", 1)[1].split()[0]
                                if len(move) > 1 and 'A' <= move[0].upper() <= 'T' and move[1:].isdigit():
                                    write_log(f"在 STDERR 佇列中找到落子結果 (進程終止): {move}")
                                    return f"= {move}\n\n"
                            except Exception as e:
                                write_log(f"解析 STDERR 中的落子結果失敗 (進程終止): {e}")
                        write_log(f"[進程終止時 STDERR]: {line}")
                    for line in temp_stderr_lines:
                        self.stderr_queue.put(line)
                return None


            # 從 stdout 佇列讀取內容
            try:
                line = self.stdout_queue.get_nowait()
                
                # 新的 GTP 回應結束判斷邏輯
                # 只要收到以 '=' 或 '?' 開頭的行，就認為這個命令的回應結束了
                # 這是為了適應 KataGo 不發送空行結束標誌的情況
                if line.strip().startswith(('=', '?')): 
                    response_started = True # 確保標記為已開始回應
                    response_lines.append(line)
                    write_log(f"在 STDOUT 中找到 GTP 回應的主要部分: '{line.strip()}'，停止等待。")
                    return "\n".join(response_lines)
                elif response_started and line == "": # 如果收到空行，則按標準 GTP 結束
                    response_lines.append(line)
                    write_log("✅ 偵測到 GTP 回應結束（空白行）")
                    return "\n".join(response_lines)
                elif response_started: # 如果已經開始回應，但不是結束標誌，則繼續收集
                    response_lines.append(line)
                # 如果還沒開始回應 (response_started = False)，且不是 '='/'?' 開頭，就忽略這些行，繼續等待

            except queue.Empty:
                pass

            # 從 stderr 佇列讀取內容
            try:
                err_line = self.stderr_queue.get_nowait()
                
                # genmove 的 stderr fallback 邏輯
                if is_genmove_like and "= " in err_line:
                    try:
                        move = err_line.split("= ", 1)[1].split()[0]
                        if len(move) > 1 and 'A' <= move[0].upper() <= 'T' and move[1:].isdigit():
                            move_from_stderr = move
                            write_log(f"在 STDERR 佇列中找到潛在落子結果: {move}")
                            if not response_lines: # 如果 stdout 沒有任何回應，使用 stderr 結果
                                write_log(f"STDOUT 無回應，使用 STDERR 落子結果: {move}")
                                return f"= {move}\n\n"
                    except Exception as e:
                        write_log(f"解析 STDERR 中的潛在落子結果失敗: {e}")
                elif err_line.strip(): # 記錄所有非空行的 stderr 輸出
                    # 為了偵錯，我們只記錄到日誌
                    pass

            except queue.Empty:
                pass

            time.sleep(0.01)

        write_log(f"指令 '{command.strip()}' 回應循環異常結束，返回內容:\n'{os.linesep.join(response_lines)}'")
        return "\n".join(response_lines)


    def parse_response(self, response):
        if response is None:
            write_log("解析回應時，輸入為 None。")
            return {"status": "error", "content": "無回應"}
        
        write_log(f"開始解析回應:\n'{response.strip()}'")
        lines = response.strip().split('\n')
        if lines and lines[-1] == "":
            lines.pop()

        for i, line in enumerate(lines):
            if line.startswith('='):
                content = "\n".join([line[1:].strip()] + lines[i+1:]).strip()
                write_log(f"解析結果: 成功，內容: '{content}'")
                return {"status": "success", "content": content}
            elif line.startswith('?'):
                content = "\n".join([line[1:].strip()] + lines[i+1:]).strip()
                write_log(f"解析結果: 錯誤，內容: '{content}'")
                return {"status": "error", "content": content}
        write_log(f"解析結果: 資訊，內容: '{response.strip()}'")
        return {"status": "info", "content": response.strip()}

    def stop_katago(self):
        if self.process and self.process.poll() is None:
            write_log("嘗試停止 KataGo 進程。")
            try:
                self._stop_io_thread.set()
                if self.io_thread and self.io_thread.is_alive():
                    self.io_thread.join(timeout=2)
                    if self.io_thread.is_alive():
                        write_log("警告: I/O 線程未能完全終止。")
                
                self.process.stdin.write("quit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=5)
                write_log("KataGo 正常結束。")
            except Exception as e:
                write_log(f"停止 KataGo 時發生錯誤，嘗試強制終止: {e}")
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                    write_log("KataGo 強制結束。")
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                    write_log("KataGo 已被 kill。")
        elif self.process:
            write_log(f"KataGo 進程已結束，退出碼：{self.process.returncode}")
        else:
            write_log("KataGo 進程未運行。")