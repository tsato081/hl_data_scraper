#!/bin/bash

# Hyperliquid Data Scraper 実行スクリプト

echo "=========================================="
echo "Hyperliquid Data Scraper"
echo "=========================================="

# Python環境チェック
if ! command -v python3 &> /dev/null; then
    echo "エラー: Python 3が見つかりません"
    exit 1
fi

# 依存関係のインストール確認
if [ ! -f "requirements.txt" ]; then
    echo "エラー: requirements.txtが見つかりません"
    exit 1
fi

echo "依存関係を確認中..."
pip3 install -r requirements.txt

# データディレクトリの作成
if [ ! -d "data" ]; then
    echo "dataディレクトリを作成します..."
    mkdir -p data
fi

echo ""
echo "Hyperliquid Data Scraperを開始します..."
echo "停止するにはCtrl+Cを押してください"
echo ""

# メインアプリケーションを実行
python3 main.py "$@"

echo ""
echo "アプリケーションが終了しました" 