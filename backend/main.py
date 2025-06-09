from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
from tempfile import NamedTemporaryFile
import os
import pyodbc # 引入 pyodbc，以便在後端捕獲其特定異常
import logging
from backend.logic import generate_api_doc # 確保這個導入路徑正確

# 配置日誌
# 設定日誌級別為 INFO，並定義日誌格式，以便追蹤程式執行情況
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# 設定 FastAPI 的根路徑，提供前端 HTML 檔案
@app.get("/", response_class=HTMLResponse)
async def get_index():
    # 確保 'frontend/index.html' 路徑在運行 FastAPI 服務時是可訪問的
    # 例如，如果 main.py 在專案根目錄，而 index.html 在 frontend/index.html
    # 則這裡的 Path 應該是相對路徑
    frontend_html_path = Path("frontend/index.html")
    if not frontend_html_path.exists():
        # 如果文件不存在，拋出 404 錯誤，並帶上詳細的錯誤訊息
        logger.error(f"前端 HTML 檔案未找到: {frontend_html_path}")
        raise HTTPException(status_code=404, detail={"message": "Frontend HTML file not found."})
    # 讀取並返回 HTML 檔案內容
    return frontend_html_path.read_text(encoding="utf-8")

@app.post("/upload/")
async def upload_files(
    word_template: UploadFile = File(...), # 上傳的 Word 範本檔案
    sql_properties: UploadFile = File(...), # 上傳的 SQL 設定檔
    server: str = Form(...), # 表單提交的資料庫伺服器名稱
    database: str = Form(...), # 表單提交的資料庫名稱
    username: str = Form(...), # 表單提交的資料庫使用者名稱
    password: str = Form(...) # 表單提交的資料庫密碼
):
    # 將資料庫連線參數組合成字典
    sql_connection_params = {
        'server': server,
        'database': database,
        'username': username,
        'password': password
    }

    tmp_word_path = None # 暫存 Word 範本的路徑
    tmp_props_path = None # 暫存 SQL properties 檔案的路徑
    output_path = None # 最終輸出文件的路徑

    try:
        # 建立臨時檔案來儲存上傳的 Word 範本檔案
        # delete=False 表示即使檔案關閉也不會自動刪除，手動刪除更可靠
        with NamedTemporaryFile(delete=False, suffix=".docx") as tmp_word:
            content = await word_template.read() # 讀取上傳檔案的內容
            if not content: # 如果內容為空，拋出錯誤
                raise HTTPException(status_code=400, detail={"message": "上傳的 Word 範本檔案為空。", "type": "EmptyFile"})
            tmp_word.write(content) # 將內容寫入臨時檔案
            tmp_word_path = Path(tmp_word.name) # 獲取臨時檔案的路徑
        logger.info(f"Word 範本已暫存至: {tmp_word_path}")

        # 建立臨時檔案來儲存上傳的 SQL properties 檔案
        with NamedTemporaryFile(delete=False, suffix=".properties") as tmp_props:
            content = await sql_properties.read() # 讀取上傳檔案的內容
            if not content: # 如果內容為空，拋出錯誤
                raise HTTPException(status_code=400, detail={"message": "上傳的 SQL 設定檔為空。", "type": "EmptyFile"})
            tmp_props.write(content) # 將內容寫入臨時檔案
            tmp_props_path = Path(tmp_props.name) # 獲取臨時檔案的路徑
        logger.info(f"SQL 設定檔已暫存至: {tmp_props_path}")

        # 定義輸出文件的路徑，建議在臨時檔案的同級目錄下創建
        output_filename = "API_規格書.docx"
        output_path = Path(tmp_word_path.parent) / output_filename # 輸出路徑為臨時檔案所在目錄下的指定檔名
        
        logger.info(f"接收到資料庫連線參數: Server={server}, Database={database}, Username={username}")

        # 呼叫您的邏輯函數來生成 API 文件
        generate_api_doc(
            sql_connection_params=sql_connection_params,
            word_template_path=tmp_word_path,
            output_path=output_path,
            sql_properties_path=tmp_props_path
        )

        logger.info(f"API 規格書 '{output_filename}' 生成成功，準備發送。")
        # 返回文件作為 HTTP 響應，並設定檔名和媒體類型
        # FileResponse 會在文件發送後自動處理檔案的關閉
        return FileResponse(path=output_path, filename=output_filename, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    except pyodbc.Error as e:
        # 捕獲 pyodbc 相關的資料庫連線或查詢錯誤
        error_message = f"資料庫連線或查詢失敗: {e}"
        logger.exception(f"資料庫錯誤: {error_message}") # 記錄詳細錯誤和堆棧追蹤
        # 返回 400 Bad Request，並帶上詳細的錯誤訊息和類型
        raise HTTPException(status_code=400, detail={"message": error_message, "type": "DatabaseError"})
    except FileNotFoundError as e:
        # 捕獲文件找不到錯誤（例如範本文件路徑不對、臨時檔案操作失敗）
        error_message = f"伺服器處理文件時找不到檔案: {e}"
        logger.exception(f"檔案未找到錯誤: {error_message}") # 記錄詳細錯誤和堆棧追蹤
        raise HTTPException(status_code=400, detail={"message": error_message, "type": "FileNotFound"})
    except HTTPException as e:
        # 捕獲已經是 HTTPException 的錯誤，直接重新拋出
        logger.warning(f"已捕獲 HTTPException: {e.detail}")
        raise e
    except Exception as e:
        # 捕獲其他所有未預期的錯誤
        error_message = f"文件生成過程中發生未知錯誤: {e}"
        logger.exception(f"未知錯誤: {error_message}") # 記錄詳細錯誤和堆棧追蹤
        # 返回 500 Internal Server Error，並帶上詳細的錯誤訊息和類型
        raise HTTPException(status_code=500, detail={"message": error_message, "type": "UnknownError"})
    finally:
        # 無論成功或失敗，都嘗試清理臨時檔案
        if tmp_word_path and tmp_word_path.exists():
            try:
                os.remove(tmp_word_path) # 刪除暫存的 Word 檔案
                logger.info(f"已刪除暫存 Word 檔案: {tmp_word_path}")
            except OSError as e:
                logger.error(f"刪除暫存 Word 檔案失敗 {tmp_word_path}: {e}")
        if tmp_props_path and tmp_props_path.exists():
            try:
                os.remove(tmp_props_path) # 刪除暫存的 SQL properties 檔案
                logger.info(f"已刪除暫存 Properties 檔案: {tmp_props_path}")
            except OSError as e:
                logger.error(f"刪除暫存 Properties 檔案失敗 {tmp_props_path}: {e}")
        # output_path (生成的最終文件) 通常由 FileResponse 管理刪除，不需要手動刪除，除非 FileResponse 沒有被返回（例如發生異常）
        # 如果 output_path 在異常發生後沒有被 FileResponse 處理，它可能仍存在。
        # 這裡可以選擇性添加清理邏輯，但要小心，避免在 FileResponse 嘗試發送後刪除它。
        # 最保險的方式是讓 FileResponse 完成其工作，或者由作業系統的臨時目錄清理機制來處理。