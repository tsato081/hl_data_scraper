# Hyperliquid Data Scraper Dockerfile
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新と必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY config.py .
COPY websocket_client.py .
COPY rest_client.py .
COPY csv_writer.py .
COPY data_manager.py .
COPY main.py .
COPY s3_client.py .

# dataディレクトリを作成
RUN mkdir -p data

# ログファイル用のディレクトリも作成
RUN mkdir -p logs

# 非rootユーザーを作成
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ヘルスチェック用のスクリプト
COPY --chown=appuser:appuser healthcheck.py .

# ヘルスチェック設定
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python healthcheck.py || exit 1

# ポート8080を公開（ヘルスチェック用）
EXPOSE 8080

# デフォルトコマンド
CMD ["python", "main.py", "--coin", "BTC", "--log-level", "INFO"] 