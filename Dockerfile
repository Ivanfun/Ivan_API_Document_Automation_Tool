# 使用包含 Python 和相容 Linux 發行版（例如 Debian 或 Ubuntu）的基礎映像
FROM debian:bookworm-slim

# 設定環境變數以進行非互動式安裝
ENV DEBIAN_FRONTEND=noninteractive

# 安裝 SQL Server ODBC Driver 18 所需的套件
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        unixodbc \
        unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
    && sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list' \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        msodbcsql18 \
        mssql-tools \
    && rm -rf /var/lib/apt/lists/*

# 設定 mssql-tools 的環境變數（可選，但建議）
ENV PATH="$PATH:/opt/mssql-tools/bin"

# 安裝 Python (例如 Python 3.10)
RUN apt-get update && apt-get install -y python3.10 python3-pip

# 在容器中設定工作目錄
WORKDIR /app

# 將您的應用程式檔案複製到容器中
COPY . /app

# 安裝 Python 依賴項
RUN pip install --no-cache-dir -r requirements.txt

# 暴露您的 FastAPI 應用程式將運行的埠號
EXPOSE 10000

# 運行您的應用程式的指令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]