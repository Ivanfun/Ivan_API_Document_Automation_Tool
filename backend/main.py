# main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
from tempfile import NamedTemporaryFile
import os
import pyodbc # 引入 pyodbc，以便在後端捕獲其特定異常
from backend.logic import generate_api_doc # 確保這個導入路徑正確

app = FastAPI()

# 設定 FastAPI 的根路徑，提供前端 HTML 檔案
@app.get("/", response_class=HTMLResponse)
async def get_index():
    # 確保 'frontend/index.html' 路徑在運行 FastAPI 服務時是可訪問的
    # 例如，如果 main.py 在專案根目錄，而 index.html 在 frontend/index.html
    # 則這裡的 Path 應該是相對路徑
    frontend_html_path = Path("frontend/index.html")
    if not frontend_html_path.exists():
        # 如果文件不存在，可以拋出錯誤或返回預設頁面
        raise HTTPException(status_code=404, detail="Frontend HTML file not found.")
    return frontend_html_path.read_text(encoding="utf-8")

@app.post("/upload/")
async def upload_files(
    word_template: UploadFile = File(...),
    sql_properties: UploadFile = File(...),
    server: str = Form(...),
    database: str = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    sql_connection_params = {
        'server': server,
        'database': database,
        'username': username,
        'password': password
    }

    tmp_word_path = None
    tmp_props_path = None
    output_path = None

    try:
        # 建立臨時檔案來儲存上傳的檔案
        with NamedTemporaryFile(delete=False, suffix=".docx") as tmp_word:
            content = await word_template.read()
            if not content:
                raise HTTPException(status_code=400, detail={"message": "上傳的 Word 範本檔案為空。"})
            tmp_word.write(content)
            tmp_word_path = Path(tmp_word.name)

        with NamedTemporaryFile(delete=False, suffix=".properties") as tmp_props:
            content = await sql_properties.read()
            if not content:
                raise HTTPException(status_code=400, detail={"message": "上傳的 SQL 設定檔為空。"})
            tmp_props.write(content)
            tmp_props_path = Path(tmp_props.name)

        # 定義輸出文件的路徑，建議在臨時檔案的同級目錄下創建
        output_filename = "API_規格書.docx"
        output_path = Path(tmp_word_path.parent) / output_filename
        
        print(f"Server: {server}, Database: {database}, Username: {username}") # 調試用日誌

        # 呼叫您的邏輯函數來生成 API 文件
        generate_api_doc(
            sql_connection_params=sql_connection_params,
            word_template_path=tmp_word_path,
            output_path=output_path,
            sql_properties_path=tmp_props_path
        )

        # 如果成功生成，則返回文件
        # FileResponse 會在文件發送後自動清理
        return FileResponse(path=output_path, filename=output_filename, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

    except pyodbc.Error as e:
        # 捕獲 pyodbc 相關的資料庫連線錯誤
        error_message = f"資料庫連線或查詢失敗: {e}"
        print(f"Database error: {error_message}") # 打印到後端日誌
        # 返回 400 Bad Request，並帶上詳細的錯誤訊息
        raise HTTPException(status_code=400, detail={"message": error_message})
    except FileNotFoundError as e:
        # 捕獲文件找不到錯誤（例如範本文件路徑不對）
        error_message = f"伺服器處理文件時找不到檔案: {e}"
        print(f"File not found error: {error_message}")
        raise HTTPException(status_code=400, detail={"message": error_message})
    except Exception as e:
        # 捕獲其他所有未預期的錯誤
        error_message = f"文件生成過程中發生未知錯誤: {e}"
        print(f"Unexpected error: {error_message}") # 打印到後端日誌
        # 返回 500 Internal Server Error，並帶上詳細的錯誤訊息
        raise HTTPException(status_code=500, detail={"message": error_message})
    finally:
        # 無論成功或失敗，都嘗試清理臨時檔案
        if tmp_word_path and tmp_word_path.exists():
            try:
                os.remove(tmp_word_path)
                print(f"Removed temp word file: {tmp_word_path}")
            except OSError as e:
                print(f"Error removing temp word file {tmp_word_path}: {e}")
        if tmp_props_path and tmp_props_path.exists():
            try:
                os.remove(tmp_props_path)
                print(f"Removed temp properties file: {tmp_props_path}")
            except OSError as e:
                print(f"Error removing temp properties file {tmp_props_path}: {e}")
        # output_path 由 FileResponse 管理刪除，通常不需要手動刪除