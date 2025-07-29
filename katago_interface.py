import subprocess
import os
import time
import select

class KataGoGTP:
    def __init__(self, katago_path=None, model_path=None, config_path=None):
        self.katago_path = katago_path or os.getenv("KATAGO_PATH", self._find_katago_path())
        self.model_path = model_path or os.getenv("KATAGO_MODEL_PATH", "/opt/homebrew/Cellar/katago/1.16.3/share/katago/kata1-b28c512nbt-s9584861952-d4960414494.bin.gz")
        self.config_path = config_path or os.getenv("KATAGO_CONFIG_PATH", "/opt/homebrew/Cellar/katago/1.16.3/share/katago/configs/gtp_example.cfg")
        self.process = None

        for path, name in [(self.katago_path, "KataGo 可執行檔"), (self.model_path, "模型檔案"), (self.config_path, "配置文件")]:
            if not os.path.exists(path):
                raise FileNotFoundError(f"{name} 找不到: {path}")

    def _find_katago_path(self):
        try:
            result = subprocess.run(['which', 'katago'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "/opt/homebrew/Cellar/katago/1.16.3/bin/katago"

    def start_katago(self):
        command = [self.katago_path, "gtp", "-model", self.model_path, "-config", self.config_path]
        print(f"啟動 KataGo 命令: {' '.join(command)}")
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
            print("KataGo 啟動成功，固定延遲 5 秒等待初始化...")
            time.sleep(5)

            # 清空初始 stderr
            try:
                while True:
                    rlist_err, _, _ = select.select([self.process.stderr], [], [], 0)
                    if rlist_err:
                        line = self.process.stderr.readline()
                        if line:
                            print(f"KataGo STDERR: {line.strip()}")
                    else:
                        break
            except Exception:
                pass
        except Exception as e:
            print(f"啟動失敗: {e}")
            self.process = None
            raise

    def send_command(self, command):
        if not self.process or self.process.poll() is not None:
            print("錯誤：KataGo 未啟動")
            return None

        full_command = command.strip() + "\n"
        print(f"-> 發送指令: {full_command.strip()}")
        try:
            self.process.stdin.write(full_command)
            self.process.stdin.flush()
        except Exception as e:
            print(f"錯誤寫入 stdin: {e}")
            return None

        response_lines = []
        is_genmove_like = command.strip().lower().startswith("genmove")
        timeout = 120 if is_genmove_like else 10
        start_time = time.time()
        move_from_stderr = None
        response_started = False

        while True:
            if time.time() - start_time > timeout:
                print(f"錯誤：KataGo 回覆超時 ({timeout}秒)。目前收到回應內容：\n" + "\n".join(response_lines))
                break

            if self.process.poll() is not None:
                print("KataGo 進程已終止")
                break

            readable, _, _ = select.select([self.process.stdout, self.process.stderr], [], [], 0.1)

            if self.process.stderr in readable:
                line = self.process.stderr.readline()
                if line:
                    stripped = line.strip()
                    print(f"<- STDERR: {stripped}")
                    if is_genmove_like and "= " in stripped:
                        try:
                            move = stripped.split("= ", 1)[1].split()[0]
                            if len(move) > 1 and 'A' <= move[0].upper() <= 'T' and move[1:].isdigit():
                                move_from_stderr = move
                        except Exception:
                            pass

            if self.process.stdout in readable:
                line = self.process.stdout.readline()
                if not line:
                    break
                stripped = line.strip()
                response_lines.append(stripped)
                print(f"<- STDOUT: {stripped}")

                if not response_started and stripped.startswith(('=', '?')):
                    response_started = True
                elif response_started and stripped == "":
                    print("✅ 偵測到 GTP 回應結束（空白行）")
                    break

        # 後補 stderr 落子結果（針對 genmove）
        stdout_has_move = any(r.strip().startswith('= ') for r in response_lines)
        if is_genmove_like and not stdout_has_move and move_from_stderr:
            return f"= {move_from_stderr}\n\n"

        return "\n".join(response_lines)

    def parse_response(self, response):
        if response is None:
            return {"status": "error", "content": "無回應"}
        lines = response.strip().split('\n')
        for i, line in enumerate(lines):
            if line.startswith('='):
                return {"status": "success", "content": "\n".join([line[1:].strip()] + lines[i+1:]).strip()}
            elif line.startswith('?'):
                return {"status": "error", "content": "\n".join([line[1:].strip()] + lines[i+1:]).strip()}
        return {"status": "info", "content": response.strip()}

    def stop_katago(self):
        if self.process and self.process.poll() is None:
            print("停止 KataGo 中...")
            try:
                self.process.stdin.write("quit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=5)
                print("KataGo 正常結束")
            except:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                    print("KataGo 強制結束")
                except:
                    self.process.kill()
                    self.process.wait()
                    print("KataGo 已被 kill")
        elif self.process:
            print(f"KataGo 已結束，退出碼：{self.process.returncode}")


# --- 互動介面 ---
if __name__ == "__main__":
    katago_client = None
    try:
        katago_client = KataGoGTP()
        katago_client.start_katago()

        print("\n✅ KataGo 介面準備就緒，可開始輸入 GTP 指令。")
        print("例如：play B D4 | genmove W | showboard | list_commands | quit")

        while True:
            user_input = input("\n請輸入 GTP 指令 (或 quit 結束): ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                break
            if user_input.lower() == "showboard":
                board = katago_client.send_command("showboard")
                print(f"📋 棋盤狀態：\n{board.strip()}")
                continue

            raw = katago_client.send_command(user_input)
            parsed = katago_client.parse_response(raw)

            if parsed['status'] == 'success':
                print(f"✅ 回應：\n{parsed['content']}")
            elif parsed['status'] == 'error':
                print(f"❌ 錯誤：{parsed['content']}")
            else:
                print(f"ℹ️ 訊息：{parsed['content']}")

    except Exception as e:
        print(f"\n🚨 發生錯誤：{e}")
    finally:
        if katago_client:
            katago_client.stop_katago()