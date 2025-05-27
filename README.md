# Hyperliquid Data Scraper

HyperliquidのBTCパーペチュアル契約から以下のデータをリアルタイムで取得し、CSVファイルに保存するPythonアプリケーションです。

## 取得データ

- **トレードデータ**: 各取引の詳細情報（価格、数量、時刻等）
- **板情報 (L2 Book)**: リアルタイムの注文板情報
- **ファンディングレート**: パーペチュアル契約のファンディングレート
- **オープンインタレスト**: 未決済建玉情報

## 特徴

- **リアルタイム収集**: WebSocketを使用した最小遅延でのデータ取得
- **自動復旧**: 接続断時の自動再接続機能
- **CSV出力**: 解析しやすいCSV形式でのデータ保存
- **ログ管理**: 詳細なログ出力とファイル保存
- **統計情報**: 定期的なデータ収集状況の報告

## 必要な環境

- Python 3.8以上
- インターネット接続

## インストール

1. **リポジトリのクローン**
```bash
git clone <repository-url>
cd HL_Data_Scraper
```

2. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本実行

```bash
python main.py
```

### コマンドラインオプション

```bash
python main.py --help
```

- `--coin, -c`: 対象通貨シンボル（デフォルト: BTC）
- `--testnet, -t`: テストネットを使用
- `--log-level, -l`: ログレベル（DEBUG, INFO, WARNING, ERROR）
- `--version, -v`: バージョン情報を表示

### 実行例

```bash
# デフォルト設定でBTCデータを収集
python main.py

# デバッグモードで実行
python main.py --log-level DEBUG

# テストネットで実行
python main.py --testnet

# 異なる通貨を指定（例: ETH）
python main.py --coin ETH
```

## 出力ファイル

アプリケーションは `data/` ディレクトリに以下のCSVファイルを作成します：

### 1. btc_trades.csv
各取引の詳細情報
```csv
timestamp,coin,side,price,size,trade_id,buyer,seller,hash,crossed,fee
2025-01-XX XX:XX:XX,BTC,B,50000.0,0.1,123456,0x...,0x...,0x...,true,
```

### 2. btc_orderbook.csv
板情報のスナップショット
```csv
timestamp,coin,bids,asks,bid_price,ask_price,bid_size,ask_size,spread
2025-01-XX XX:XX:XX,BTC,[...],[...],49999.5,50000.5,1.0,0.5,1.0
```

### 3. btc_funding_rate.csv
ファンディングレート情報
```csv
timestamp,coin,funding_rate,predicted_funding_rate,funding_time,mark_price,index_price
2025-01-XX XX:XX:XX,BTC,0.0001,,50000.0,50000.0
```

### 4. btc_open_interest.csv
オープンインタレスト情報
```csv
timestamp,coin,open_interest,mark_price,oracle_price
2025-01-XX XX:XX:XX,BTC,1000000,50000.0,50000.0
```

## 設定

`config.py` ファイルで以下の設定を変更できます：

- **API URL**: WebSocketとHTTPS APIのエンドポイント
- **更新間隔**: 各データの取得間隔
- **CSV出力設定**: ファイル名や出力ディレクトリ
- **ログ設定**: ログレベルやファイル名

## ログ

- **コンソール出力**: リアルタイムでのステータス表示
- **ファイル出力**: `hyperliquid_scraper.log` にログ保存
- **定期統計**: 5分間隔でCSVファイルの統計情報を出力

## エラーハンドリング

- **自動再接続**: WebSocket接続断時の自動復旧
- **リトライ機能**: API呼び出し失敗時のリトライ
- **エラーログ**: 詳細なエラー情報の記録

## 停止方法

- **Ctrl+C**: 安全な停止（データ保存完了後に終了）
- **SIGTERM**: プロセス終了シグナル

## データ活用例

### Pythonでの読み込み

```python
import pandas as pd

# トレードデータの読み込み
trades_df = pd.read_csv('data/btc_trades.csv')
trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])

# 価格の統計
print(trades_df['price'].describe())

# 時系列プロット
import matplotlib.pyplot as plt
plt.plot(trades_df['timestamp'], trades_df['price'])
plt.show()
```

### 板情報の解析

```python
import json
import pandas as pd

# 板情報の読み込み
orderbook_df = pd.read_csv('data/btc_orderbook.csv')

# 最新の板情報
latest = orderbook_df.iloc[-1]
bids = json.loads(latest['bids'].replace("'", '"'))
asks = json.loads(latest['asks'].replace("'", '"'))

print(f"Best Bid: {latest['bid_price']} ({latest['bid_size']})")
print(f"Best Ask: {latest['ask_price']} ({latest['ask_size']})")
print(f"Spread: {latest['spread']}")
```

## トラブルシューティング

### 接続エラー
- インターネット接続を確認
- ファイアウォール設定を確認
- Hyperliquid APIの稼働状況を確認

### ファイル書き込みエラー
- ディスク容量を確認
- 書き込み権限を確認
- CSVファイルが他のプログラムで開かれていないか確認

### メモリエラー
- 長時間実行時は定期的にCSVファイルをアーカイブ
- ログレベルをINFOまたはWARNINGに変更

## API仕様

このアプリケーションはHyperliquidの公式APIを使用しています：

- **WebSocket API**: `wss://api.hyperliquid.xyz/ws`
- **REST API**: `https://api.hyperliquid.xyz/info`
- **ドキュメント**: [Hyperliquid API Documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api)

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 免責事項

このソフトウェアは教育および研究目的で提供されています。金融取引における利用については自己責任でお願いします。データの正確性や完全性については保証いたしません。 