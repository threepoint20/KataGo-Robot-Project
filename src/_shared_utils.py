# _shared_utils.py
import datetime
import os

LOG_FILE_PATH = "katago_debug_log.txt" # 日誌檔路徑，可以根據需要調整

def write_log(message):
    """將偵錯訊息寫入日誌檔並列印到控制台"""
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3] # 精確到毫秒
    log_message = f"{timestamp} {message}"
    
    # 初始化時清空日誌檔，但只在首次寫入時執行
    if not hasattr(write_log, 'file_initialized'):
        if os.path.exists(LOG_FILE_PATH):
            os.remove(LOG_FILE_PATH)
            print(f"舊的日誌檔 '{LOG_FILE_PATH}' 已清除。")
        write_log.file_initialized = True # 設定標誌，避免重複清除

    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(f"{log_message}\n")
    print(log_message) # 同時列印到控制台，方便實時觀察

# 將日誌初始化邏輯移到這裡，確保只執行一次
if __name__ == "__main__":
    # 這個區塊在直接運行 _shared_utils.py 時會執行
    # 測試日誌功能
    write_log("_shared_utils.py 已初始化。")
    write_log("這是一條測試日誌訊息。")