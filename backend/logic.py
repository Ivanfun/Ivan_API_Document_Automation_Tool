import pandas as pd
import numpy as np # 引入 numpy 來處理 NaN 
from docx import Document
from docx.shared import Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path
import pyodbc

def load_sql_properties(path):
    """
    從指定的檔案路徑載入 SQL 查詢的屬性。
    檔案格式應為 key=value，並忽略以 '#' 開頭的註解行。
    """
    sql_dict = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            # 檢查行中是否包含 '=' 且不是註解行
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1) # 只在第一個 '=' 處分割
                sql_dict[key.strip()] = val.strip() # 移除鍵和值的空白字元
    return sql_dict

def generate_api_doc(sql_connection_params: dict, word_template_path: Path, output_path: Path, sql_properties_path: Path):
    """
    根據資料庫中的API資訊和SQL屬性檔案，生成API說明文件。

    Args:
        sql_connection_params (dict): 資料庫連線參數，包含 'server', 'database', 'username', 'password'。
        word_template_path (Path): Word 文件範本的路徑。
        output_path (Path): 輸出 Word 文件的路徑。
        sql_properties_path (Path): 包含 SQL 查詢語法的屬性檔案路徑。
    """
    # 資料庫連線參數
    server = sql_connection_params['server']
    database = sql_connection_params['database']
    username = sql_connection_params['username']
    password = sql_connection_params['password']

    conn = None # 初始化 conn 變數，確保在 finally 區塊中可以安全地關閉連線
    try:
        # 建立資料庫連線 (使用 ODBC Driver 18 for SQL Server)
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            f"TrustServerCertificate=yes;" # 信任伺服器憑證
        )

        # 查詢 API 階層表資訊
        api_hierarchy_df = pd.read_sql("""
            select
                a.FLOW_ID as "批次代碼"
                ,a.FLOW_HELP as "批次說明"
                ,class_num as "API順序"
                ,b.CALL_CODE_ID as "API代碼"
                ,c.API_DESC as "API說明"
            from JH_WS02_FLOW_LIST a
                inner join JH_WS02_FLOW_SCHEDULE_LIST b
                on a.pk = b.FLOW_ID_PK
                inner join JH_WS02_CODE_LIST c
                on b.CALL_CODE_ID = c.CODE_ID
            where FLOW_ID like 'FI_%'
            order by a.FLOW_HELP,CLASS_NUM
        """, conn)

        # 處理 API 階層表資料為空的情況
        if api_hierarchy_df.empty:
            doc = Document(word_template_path)
            doc.add_paragraph("資料庫中找不到 'API階層表' 的資料。")
            doc.save(output_path)
            return # 若無資料則直接結束函式

        api_data = {} # 用於儲存每個 API 代碼相關的所有資料

        # 查詢 API 清單資訊
        api_list_df = pd.read_sql("""
            select
                CODE_ID AS [API代碼]
                ,API_DESC AS [API簡述]
                ,REPLACE(REPLACE(CODE_HELP,CHAR(13)+CHAR(10),''),CHAR(10),'') AS [API說明]
                ,CASE EXEC_TYPE WHEN '0' THEN 'SQL' ELSE 'SSH' END AS [API行為類型]
                ,JNDI_USE AS [資料庫連線名稱]
                ,REPLACE(ACTION_TYPE,CHAR(13)+CHAR(10),'') AS [執行類型]
                ,REPLACE(SQL_PROP_KEY,CHAR(13)+CHAR(10),'') AS [語法設定鍵值]
                ,'DFMDB_authority' AS [驗證金鑰]
                ,CASE IS_ENCODE WHEN 'Y' THEN '是' ELSE '否' END AS [是否編碼]
            FROM JH_WS02_CODE_LIST
            where CODE_ID in (
                                select DISTINCT Y.CALL_CODE_ID as "API代碼"
                                from JH_WS02_FLOW_LIST X
                                    inner join JH_WS02_FLOW_SCHEDULE_LIST Y
                                    on X.pk = Y.FLOW_ID_PK
                                    inner join JH_WS02_CODE_LIST Z
                                    on Y.CALL_CODE_ID = Z.CODE_ID
                                where FLOW_ID like 'FI_%'
                            )
        """, conn)
        # 將 API 清單資料按 API 代碼儲存到 api_data 字典中
        for api_code in api_list_df['API代碼'].dropna().unique():
            if api_code not in api_data:
                api_data[api_code] = {}
            api_data[api_code]['API清單'] = api_list_df[api_list_df['API代碼'] == api_code]

        # 查詢輸出設定資訊
        output_setting_df = pd.read_sql("""
            SELECT A.CODE_ID AS [API代碼]
                ,ISNULL(B.CLASS_NUM,'') AS [節點階層]
                ,ISNULL(B.UP_PK_FIELD,'') AS [父階層關聯鍵值]
                ,ISNULL(B.DOWN_PK_FIELD,'') AS [子階層關聯鍵值]
                ,ISNULL(B.OUTPUT_FIELD,'') AS [輸出參數]
            FROM JH_WS02_CODE_LIST A
                LEFT JOIN JH_WS02_CODE_FORMAT_LIST B
                ON A.PK =B.CODE_ID_PK
            where CODE_ID in (
                                select DISTINCT Y.CALL_CODE_ID as "API代碼"
                                from JH_WS02_FLOW_LIST X
                                    inner join JH_WS02_FLOW_SCHEDULE_LIST Y
                                    on X.pk = Y.FLOW_ID_PK
                                    inner join JH_WS02_CODE_LIST Z
                                    on Y.CALL_CODE_ID = Z.CODE_ID
                                where FLOW_ID like 'FI_%'
                            )
            ORDER BY 1,2
        """, conn)
        # 將輸出設定資料按 API 代碼儲存
        for api_code in output_setting_df['API代碼'].dropna().unique():
            if api_code not in api_data:
                api_data[api_code] = {}
            api_data[api_code]['輸出設定'] = output_setting_df[output_setting_df['API代碼'] == api_code]

        # 查詢 IP 權限設定資訊
        ip_permission_df = pd.read_sql("""
            SELECT A.CODE_ID AS [API代碼]
                ,B.ACCESSED_IP AS [IP]
                ,ISNULL(B.ACCESSED_DESC,'') AS [說明]
            FROM JH_WS02_CODE_LIST A
                LEFT JOIN JH_WS02_CODE_IP_RELATION B
                ON A.PK =B.CODE_ID_PK
            where CODE_ID in (
                                select DISTINCT Y.CALL_CODE_ID as "API代碼"
                                from JH_WS02_FLOW_LIST X
                                    inner join JH_WS02_FLOW_SCHEDULE_LIST Y
                                    on X.pk = Y.FLOW_ID_PK
                                    inner join JH_WS02_CODE_LIST Z
                                    on Y.CALL_CODE_ID = Z.CODE_ID
                                where FLOW_ID like 'FI_%'
                            )
            ORDER BY 1,2
        """, conn)
        # 將 IP 權限設定資料按 API 代碼儲存
        for api_code in ip_permission_df['API代碼'].dropna().unique():
            if api_code not in api_data:
                api_data[api_code] = {}
            api_data[api_code]['IP權限設定'] = ip_permission_df[ip_permission_df['API代碼'] == api_code]

        # 查詢 WebService 資訊
        webservice_df = pd.read_sql("""
            SELECT A.CODE_ID AS [API代碼]
                ,B.CLASS_NUM AS [序]
                ,ISNULL(B.WEB_SERVICE_CODE,'') AS [主機代碼]
                ,CASE B.WEB_SERVICE_CODE WHEN 'WS01' THEN 'Middle01' WHEN 'WS02' THEN 'Middle02' END AS [主機名稱]
                ,CASE B.WEB_SERVICE_CODE WHEN 'WS01' THEN '192.168.222.136' WHEN 'WS02' THEN '192.168.222.138' END AS [主機IP]
                ,CASE B.IS_DOING WHEN 'Y' THEN '是' ELSE '否' END AS [啟用]
            FROM JH_WS02_CODE_LIST A
                LEFT JOIN JH_WS02_CODE_WS_RELATION B
                ON A.PK =B.CODE_ID_PK
            where CODE_ID in (
                                select DISTINCT Y.CALL_CODE_ID as "API代碼"
                                from JH_WS02_FLOW_LIST X
                                    inner join JH_WS02_FLOW_SCHEDULE_LIST Y
                                    on X.pk = Y.FLOW_ID_PK
                                    inner join JH_WS02_CODE_LIST Z
                                    on Y.CALL_CODE_ID = Z.CODE_ID
                                where FLOW_ID like 'FI_%'
                            )
            ORDER BY 1,2
        """, conn)
        # 將 WebService 資料按 API 代碼儲存
        for api_code in webservice_df['API代碼'].dropna().unique():
            if api_code not in api_data:
                api_data[api_code] = {}
            api_data[api_code]['WebService'] = webservice_df[webservice_df['API代碼'] == api_code]

        # 查詢參數驗證資訊
        param_validation_df = pd.read_sql("""
            SELECT A.CODE_ID AS [API代碼]
                ,ROW_NUMBER() OVER (PARTITION BY A.CODE_ID ORDER BY B.FORMAT_IDX) AS [序]
                ,ISNULL(B.INPUT_FIELD,'') AS [屬性名]
                ,ISNULL(B.INPUT_DEFAULT_VAL,'') AS [預設值]
                ,ISNULL(REPLACE(B.REG_DESC,CHAR(13)+CHAR(10),'') ,'') AS [說明]
            FROM JH_WS02_CODE_LIST A
                LEFT JOIN JH_WS02_CODE_RANGE_ANALYSIS B
                ON A.PK =B.CODE_ID_PK
            where CODE_ID in (
                                select DISTINCT Y.CALL_CODE_ID as "API代碼"
                                from JH_WS02_FLOW_LIST X
                                    inner join JH_WS02_FLOW_SCHEDULE_LIST Y
                                    on X.pk = Y.FLOW_ID_PK
                                    inner join JH_WS02_CODE_LIST Z
                                    on Y.CALL_CODE_ID = Z.CODE_ID
                                where FLOW_ID like 'FI_%'
                            )
            ORDER BY 1,2
        """, conn)
        # 將參數驗證資料按 API 代碼儲存
        for api_code in param_validation_df['API代碼'].dropna().unique():
            if api_code not in api_data:
                api_data[api_code] = {}
            api_data[api_code]['參數驗證'] = param_validation_df[param_validation_df['API代碼'] == api_code]

        # 載入 SQL 屬性檔案（包含實際的 SQL 語法）
        sql_map = load_sql_properties(sql_properties_path)
        # 載入 Word 範本文件
        doc = Document(word_template_path)

        # 遍歷批次清單，為每個批次生成文件內容
        batch_list = api_hierarchy_df[['批次代碼', '批次說明']].drop_duplicates()
        for row in batch_list.itertuples(index=False):
            batch_code, batch_desc = row
            # 根據批次代碼和說明篩選相關的 API 階層資料
            group_df = api_hierarchy_df[
                (api_hierarchy_df['批次代碼'] == batch_code) &
                (api_hierarchy_df['批次說明'] == batch_desc)
            ]

            doc.add_paragraph(f'{batch_code} ({batch_desc})', style='Heading 2')
            
            # API 階層表 (固定顯示，即使沒有 API 也會顯示表頭)
            api_list_table = doc.add_table(rows=1, cols=3)
            api_list_table.style = 'Table Grid'
            api_list_table.autofit = False
            headers = ['順序', 'API代碼', 'API說明']
            widths_cm = [1.24, 7, 10.79]

            # 設定表頭
            for i in range(3):
                cell = api_list_table.cell(0, i)
                cell.text = headers[i]
                cell.width = Cm(widths_cm[i])
                tcPr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:fill'), "D9D9D9") # 設定表頭背景色
                tcPr.append(shd)

            # 處理 API 階層表資料，檢查每個值是否為 NaN 或空字串
            if group_df.empty:
                cells = api_list_table.add_row().cells
                cells[0].text = "NaN"
                cells[1].text = "NaN"
                cells[2].text = "NaN"
                for i in range(3):
                    cells[i].width = Cm(widths_cm[i])
            else:
                for _, api_row in group_df.iterrows():
                    cells = api_list_table.add_row().cells
                    # 檢查每個欄位，如果是 NaN 或空字串，則顯示 "NaN"
                    seq_val = api_row['API順序']
                    cells[0].text = str(int(seq_val)) if pd.notna(seq_val) and float(seq_val).is_integer() else "NaN"
                    cells[1].text = str(api_row['API代碼']) if pd.notna(api_row['API代碼']) and str(api_row['API代碼']).strip() != '' else "NaN"
                    cells[2].text = str(api_row['API說明']) if pd.notna(api_row['API說明']) and str(api_row['API說明']).strip() != '' else "NaN"
                    for i in range(3):
                        cells[i].width = Cm(widths_cm[i])

            doc.add_paragraph('') # 加入空行作為間隔

            # 如果 group_df 是空的，表示該批次下沒有任何 API，則不再為此批次處理詳細 API 資訊
            if group_df.empty:
                continue

            # 遍歷每個批次下的 API，生成詳細資訊
            for _, api_row in group_df.iterrows():
                api_code = api_row['API代碼']
                doc.add_paragraph(api_code, style='Heading 4') # 加入 API 代碼標題
                
                # API 清單表格的表頭設定 (總是會創建表頭)
                api_detail_table = doc.add_table(rows=1, cols=3)
                api_detail_table.style = 'Table Grid'
                api_detail_table.autofit = False
                headers_api_list = ['序', '參數', '設定值']
                widths_cm_api_list = [1.24, 3.5, 14.29]

                for i in range(3):
                    cell = api_detail_table.cell(0, i)
                    cell.text = headers_api_list[i]
                    cell.width = Cm(widths_cm_api_list[i])
                    tcPr = cell._tc.get_or_add_tcPr()
                    shd = OxmlElement('w:shd')
                    shd.set(qn('w:fill'), "D9D9D9")
                    tcPr.append(shd)

                api_df = api_data.get(api_code, {}).get('API清單')
                
                # 判斷 API 清單是否有資料，如果沒有則填充 NaN
                if api_df is not None and not api_df.empty:
                    param_names = [
                        'API代碼', 'API簡述', 'API說明', 'API行為類型', '資料庫連線名稱',
                        '執行類型', '語法設定鍵值', '驗證金鑰', '是否編碼', '語法'
                    ]
                    for i, param in enumerate(param_names, start=1):
                        row_cells = api_detail_table.add_row().cells
                        row_cells[0].text = str(i)
                        row_cells[1].text = param
                        
                        value_to_display = "NaN" # 預設值為 "NaN"

                        if param == '語法':
                            # 取得 SQL 語法設定鍵值並從 sql_map 中查詢實際語法
                            config_key_val = api_df['語法設定鍵值'].iloc[0]
                            if pd.notna(config_key_val) and str(config_key_val).strip() != '':
                                raw_value = sql_map.get(str(config_key_val), ' 查無對應 SQL')
                                # 替換特殊字元，使其在 Word 中正確顯示換行和 tab
                                value_to_display = raw_value.replace('\\n', '\n').replace('\\t', '\t').replace('\\=', '=')
                            # else: 保持 value_to_display 為 "NaN"
                        else:
                            # 取得其他參數的值，並檢查是否為空字串或 NaN
                            if param in api_df.columns:
                                val_from_df = api_df[param].iloc[0]
                                if pd.notna(val_from_df) and str(val_from_df).strip() != '':
                                    value_to_display = str(val_from_df)
                                # else: 保持 value_to_display 為 "NaN"
                            # else: 保持 value_to_display 為 "NaN"

                        row_cells[2].text = value_to_display
                        for j in range(3):
                            row_cells[j].width = Cm(widths_cm_api_list[j])
                        for j in [0, 1]: # 設定前兩列的背景色
                            tcPr = row_cells[j]._tc.get_or_add_tcPr()
                            shd = OxmlElement('w:shd')
                            shd.set(qn('w:fill'), "F2F2F2")
                            tcPr.append(shd)
                else:
                    # 如果 API 清單為空，在表格中添加一行並填入 "NaN"
                    row_cells = api_detail_table.add_row().cells
                    row_cells[0].text = "NaN"
                    row_cells[1].text = "NaN"
                    row_cells[2].text = "NaN"
                    for j in range(3):
                        row_cells[j].width = Cm(widths_cm_api_list[j])

                doc.add_paragraph('') # 加入空行作為間隔

                # 定義其他 API 相關區塊的順序、表頭和寬度
                section_order = [
                    ('參數驗證', ['序', '屬性名', '預設值', '說明'], [1.24, 3.5, 8.89, 5.4]),
                    ('WebService', ['序', '主機代碼', '主機名稱', '主機IP', '啟用'], [1.24, 3.5, 4.57, 4.32, 5.4]),
                    ('IP權限設定', ['IP', '說明'], [8.74, 10.25]),
                    ('輸出設定', ['節點階層', '父階層關聯鍵值', '子階層關聯鍵值', '輸出參數'], [3.24, 4.5, 5.89, 5.4])
                ]
                
                # 遍歷每個區塊並生成其表格
                for sheet_name, headers, widths_cm in section_order:
                    doc.add_paragraph(sheet_name, style='Heading 5')
                    table = doc.add_table(rows=1, cols=len(headers))
                    table.style = 'Table Grid'
                    table.autofit = False
                    
                    # 設定表格的表頭
                    for i, header in enumerate(headers):
                        cell = table.cell(0, i)
                        cell.text = header
                        cell.width = Cm(widths_cm[i])
                        tcPr = cell._tc.get_or_add_tcPr()
                        shd = OxmlElement('w:shd')
                        shd.set(qn('w:fill'), "D9D9D9")
                        tcPr.append(shd)

                    df = api_data.get(api_code, {}).get(sheet_name)
                    
                    # 判斷當前資料框是否有資料，如果沒有則填充 NaN
                    if df is not None and not df.empty:
                        for _, row_data in df.iterrows():
                            row_cells = table.add_row().cells
                            for j, header in enumerate(headers):
                                # 針對每個單元格的值，檢查是否為空字串或 NaN，然後填充 "NaN"
                                value = row_data.get(header, '') # 從 DataFrame 取得值，預設為空字串

                                display_value = "NaN" # 預設顯示 "NaN"

                                # 如果值不是 NaN 且去除前後空白後不為空字串
                                if pd.notna(value) and str(value).strip() != '':
                                    # 特殊處理 '序' 和 '節點階層' 欄位，轉換為整數顯示
                                    if header in ['序', '節點階層']:
                                        try:
                                            # 如果是浮點數且為整數值，則轉換為整數
                                            display_value = str(int(value)) if float(value).is_integer() else str(value)
                                        except ValueError:
                                            display_value = str(value) # 無法轉換則保持原字串
                                    else:
                                        display_value = str(value) # 其他欄位直接使用字串形式

                                row_cells[j].text = display_value
                                row_cells[j].width = Cm(widths_cm[j])
                    else:
                        # 如果此區塊的 DataFrame 為空，在表格中添加一行並填入 "NaN"
                        row_cells = table.add_row().cells
                        for j in range(len(headers)):
                            row_cells[j].text = "NaN"
                            row_cells[j].width = Cm(widths_cm[j])
                    doc.add_paragraph('')

        # 儲存最終的 Word 文件
        doc.save(output_path)

    finally:
        # 確保在函式結束時關閉資料庫連線
        if conn:
            conn.close()