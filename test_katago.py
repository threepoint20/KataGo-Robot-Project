import subprocess
import os
import sys

KATAGO_PATH = "/opt/homebrew/Cellar/katago/1.16.3/bin/katago"
MODEL_PATH = "/opt/homebrew/Cellar/katago/1.16.3/share/katago/kata1-b28c512nbt-s9584861952-d4960414494.bin.gz"
CONFIG_PATH = "/opt/homebrew/Cellar/katago/1.16.3/share/katago/configs/gtp_example.cfg"

def check_paths():
    for path in [KATAGO_PATH, MODEL_PATH, CONFIG_PATH]:
        if not os.path.exists(path):
            print(f"錯誤：路徑不存在 - {path}")
            sys.exit(1)
        print(f"路徑存在：{path}")

def run_katago():
    command = [KATAGO_PATH, "gtp", "-model", MODEL_PATH, "-config", CONFIG_PATH]
    print(f"執行命令: {' '.join(command)}")
    print(f"當前工作目錄: {os.getcwd()}")
    print(f"Python 環境 PATH: {os.environ.get('PATH')}")
    
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        print("KataGo 進程啟動，PID:", process.pid)
        
        while True:
            stderr_line = process.stderr.readline()
            stdout_line = process.stdout.readline()
            if stderr_line:
                print(f"STDERR: {stderr_line.strip()}")
            if stdout_line:
                print(f"STDOUT: {stdout_line.strip()}")
            if "GTP ready, beginning main protocol loop" in stderr_line or \
               "GTP ready, beginning main protocol loop" in stdout_line:
                print("KataGo 準備就緒")
                break
            if process.poll() is not None:
                raise Exception(f"KataGo 意外退出，退出碼: {process.returncode}")
        
        # 測試一個簡單的 GTP 指令
        process.stdin.write("name\n")
        process.stdin.flush()
        response = []
        while True:
            line = process.stdout.readline().strip()
            print(f"回覆: {line}")
            response.append(line)
            if line == "":
                break
        print("KataGo 回覆:", response)
        
        # 結束進程
        process.stdin.write("quit\n")
        process.stdin.flush()
        process.wait(timeout=5)
        print("KataGo 已正常退出")
        
    except Exception as e:
        print(f"錯誤: {e}")
        if process.poll() is not None:
            print(f"KataGo 退出碼: {process.returncode}")

if __name__ == "__main__":
    check_paths()
    run_katago()