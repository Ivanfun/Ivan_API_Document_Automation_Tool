
--==============================================
--API清單
select 
       CODE_ID AS [API代碼]
      ,API_DESC AS 	[API簡述]
      ,REPLACE(CODE_HELP,CHAR(13)+CHAR(10),'') AS 	[API說明]
      ,CASE EXEC_TYPE WHEN '0' THEN 'SQL' ELSE 'SSH' END AS [API行為類型]
      ,JNDI_USE AS [資料庫連線名稱]
      ,ACTION_TYPE AS [執行類型]
      ,SQL_PROP_KEY AS [語法設定鍵值]
      ,'DFMDB_authority'	AS [驗證金鑰]
      ,CASE IS_ENCODE WHEN 'Y' THEN '是' ELSE '否' END AS [是否編碼]
  FROM JH_WS02_CODE_LIST
 where CODE_ID in (
                     'T2T_01_MULTIPLE_API'
                    ,'T2T_11_MULTIPLE_API'
                    ,'T2T_21_MULTIPLE_API'
                    ,'T2T_22_MULTIPLE_API'
                    ,'T2T_31C_MULTIPLE_API'
                    ,'EXEC_SP_JHSP_LOD_STG_TMP01'
                    ,'EXEC_SP_JHSP_LOD_STG_TMP02'
                    ,'EXEC_SP_JHSP_LOD_STG_TMP03'
                    ,'EXEC_SP_JHSP_LOD_STG_TMP04'
                    ,'EXEC_SP_JHSP_LOD_STG_TMP05'
                  )


--==============================================
--輸出設定

SELECT A.CODE_ID AS [API代碼]
      ,ISNULL(B.CLASS_NUM,'') AS [節點階層]
      ,ISNULL(B.UP_PK_FIELD,'') AS [父階層關聯鍵值]
	    ,ISNULL(B.DOWN_PK_FIELD,'') AS [子階層關聯鍵值]	
      ,ISNULL(B.OUTPUT_FIELD,'') AS [輸出參數]
  FROM JH_WS02_CODE_LIST A
       LEFT JOIN JH_WS02_CODE_FORMAT_LIST B
       ON A.PK =B.CODE_ID_PK
 where CODE_ID in (
                    'T2T_01_MULTIPLE_API'
                   ,'T2T_11_MULTIPLE_API'
                   ,'T2T_21_MULTIPLE_API'
                   ,'T2T_22_MULTIPLE_API'
                   ,'T2T_31C_MULTIPLE_API'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP01'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP02'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP03'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP04'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP05'
                  )
 ORDER BY 1,2


--=================================
--IP權限設定

SELECT A.CODE_ID AS [API代碼]
      ,B.ACCESSED_IP AS [IP]
      ,ISNULL(B.ACCESSED_DESC,'') AS [說明]
  FROM JH_WS02_CODE_LIST A
       LEFT JOIN JH_WS02_CODE_IP_RELATION B
       ON A.PK =B.CODE_ID_PK
 where CODE_ID in (
                    'T2T_01_MULTIPLE_API'
                   ,'T2T_11_MULTIPLE_API'
                   ,'T2T_21_MULTIPLE_API'
                   ,'T2T_22_MULTIPLE_API'
                   ,'T2T_31C_MULTIPLE_API'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP01'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP02'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP03'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP04'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP05'
                  )
 ORDER BY 1,2


--=================================
--WebService

SELECT A.CODE_ID AS [API代碼]
      ,B.CLASS_NUM AS [序]
      ,ISNULL(B.WEB_SERVICE_CODE,'') AS [主機代碼]
      ,CASE B.WEB_SERVICE_CODE WHEN 'WS01' THEN 'Middle01' WHEN 'WS02' THEN 'Middle02' END AS [主機名稱]
      ,CASE B.WEB_SERVICE_CODE WHEN 'WS01' THEN '192.168.222.136' WHEN 'WS02' THEN '192.168.222.138' END AS [主機IP]
      ,CASE B.IS_DOING WHEN 'Y' THEN '是' ELSE '否' END  AS [主機代碼]
  FROM JH_WS02_CODE_LIST A
       LEFT JOIN JH_WS02_CODE_WS_RELATION B
       ON A.PK =B.CODE_ID_PK
 where CODE_ID in (
                   'T2T_01_MULTIPLE_API'
                   ,'T2T_11_MULTIPLE_API'
                   ,'T2T_21_MULTIPLE_API'
                   ,'T2T_22_MULTIPLE_API'
                   ,'T2T_31C_MULTIPLE_API'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP01'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP02'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP03'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP04'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP05'
                  )
 ORDER BY 1,2

--=================================
--參數驗證

SELECT A.CODE_ID AS [API代碼]
      ,ROW_NUMBER() OVER (PARTITION BY A.CODE_ID ORDER BY B.FORMAT_IDX) AS  [序]
      ,ISNULL(B.INPUT_FIELD,'') AS [屬性名]
      ,ISNULL(B.INPUT_DEFAULT_VAL,'') AS [預設值]
      ,ISNULL(REPLACE(B.REG_DESC,CHAR(13)+CHAR(10),'') ,'') AS [說明]
  FROM JH_WS02_CODE_LIST A
       LEFT JOIN JH_WS02_CODE_RANGE_ANALYSIS B
       ON A.PK =B.CODE_ID_PK
 where CODE_ID in (
                   'T2T_01_MULTIPLE_API'
                   ,'T2T_11_MULTIPLE_API'
                   ,'T2T_21_MULTIPLE_API'
                   ,'T2T_22_MULTIPLE_API'
                   ,'T2T_31C_MULTIPLE_API'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP01'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP02'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP03'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP04'
                   ,'EXEC_SP_JHSP_LOD_STG_TMP05'
                  )
 ORDER BY 1,2



