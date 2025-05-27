#!/bin/bash
set -e

# Hyperliquid Data Scraper Docker エントリーポイント

echo "=========================================="
echo "Hyperliquid Data Scraper Docker Container"
echo "=========================================="

# 環境変数の設定
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app

# タイムゾーンの設定
if [ -n "$TZ" ]; then
    echo "タイムゾーンを設定: $TZ"
fi

# ディレクトリの作成・権限設定
echo "ディレクトリを初期化しています..."
mkdir -p /app/data
mkdir -p /app/logs
chmod 755 /app/data
chmod 755 /app/logs

# ファイル権限の確認
echo "ファイル権限を確認しています..."
if [ ! -w /app/data ]; then
    echo "警告: dataディレクトリに書き込み権限がありません"
fi

if [ ! -w /app/logs ]; then
    echo "警告: logsディレクトリに書き込み権限がありません"
fi

# Python環境の確認
echo "Python環境を確認しています..."
python --version
pip list | grep -E "(websockets|requests|pandas|aiohttp|asyncio-throttle|python-dotenv)"

# 接続テスト（オプション）
if [ "$SKIP_CONNECTION_TEST" != "true" ]; then
    echo "Hyperliquid API接続テストを実行しています..."
    timeout 30 python test_connection.py || {
        echo "警告: 接続テストに失敗しましたが、アプリケーションを開始します"
    }
fi

# ヘルスチェックスクリプトの権限設定
chmod +x /app/healthcheck.py

echo "初期化完了。アプリケーションを開始します..."
echo "=========================================="

# コマンドライン引数の処理
if [ $# -eq 0 ]; then
    # デフォルトコマンド
    exec python main.py --coin BTC --log-level INFO
else
    # 引数が指定された場合はそれを実行
    exec "$@"
fi 