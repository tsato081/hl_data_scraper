# Hyperliquid Data Scraper Configuration

import os

# Hyperliquid API URLs
WEBSOCKET_URL = "wss://api.hyperliquid.xyz/ws"
HTTPS_BASE_URL = "https://api.hyperliquid.xyz"

# Coin settings
BTC_COIN = "BTC"  # BTCパーペチュアルの識別子

# CSV output settings
CSV_OUTPUT_DIR = "data"
CSV_FILES = {
    "trades": "btc_trades.csv",
    "orderbook": "btc_orderbook.csv",
    "funding_rate": "btc_funding_rate.csv",
    "open_interest": "btc_open_interest.csv"
}

# Data collection intervals (seconds)
ORDERBOOK_UPDATE_INTERVAL = 0.5  # 0.5秒ごとに板情報を更新
FUNDING_RATE_UPDATE_INTERVAL = 60  # 1分ごとにファンディングレートをチェック
OPEN_INTEREST_UPDATE_INTERVAL = 60  # 1分ごとにオープンインタレストをチェック

# WebSocket heartbeat interval
HEARTBEAT_INTERVAL = 30

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5

# Logging settings
LOG_LEVEL = "INFO"
LOG_FILE = "hyperliquid_scraper.log"

# AWS S3 settings
USE_S3 = os.getenv('USE_S3', 'false').lower() == 'true'  # デフォルトは無効
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'hyperliquid-data-bucket')  # S3バケット名
S3_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')  # AWSリージョン
S3_KEY_PREFIX = os.getenv('S3_KEY_PREFIX', 'hyperliquid-data/')  # S3キープレフィックス
S3_UPLOAD_INTERVAL = int(os.getenv('S3_UPLOAD_INTERVAL', '300'))  # 5分間隔でS3にアップロード（秒）

# S3アップロード設定
S3_COMPRESS_FILES = os.getenv('S3_COMPRESS_FILES', 'true').lower() == 'true'  # ファイルを圧縮してアップロード
S3_BACKUP_LOCAL_FILES = os.getenv('S3_BACKUP_LOCAL_FILES', 'true').lower() == 'true'  # ローカルファイルもバックアップとして保持

# CSV columns
TRADES_COLUMNS = [
    "timestamp", "coin", "side", "price", "size", "trade_id", 
    "buyer", "seller", "hash", "crossed", "fee"
]

ORDERBOOK_COLUMNS = [
    "timestamp", "coin", "bids", "asks", "bid_price", "ask_price",
    "bid_size", "ask_size", "spread"
]

FUNDING_RATE_COLUMNS = [
    "timestamp", "coin", "funding_rate", "predicted_funding_rate", 
    "funding_time", "mark_price", "index_price"
]

OPEN_INTEREST_COLUMNS = [
    "timestamp", "coin", "open_interest", "mark_price", "oracle_price"
] 