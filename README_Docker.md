# Hyperliquid Data Scraper - Docker デプロイメントガイド

このドキュメントでは、Hyperliquid Data ScraperをDockerを使用してデプロイする方法について説明します。

## 📋 前提条件

- **Docker**: 20.10以上
- **Docker Compose**: v2.0以上
- **OS**: Amazon Linux 2, Ubuntu 20.04以上
- **メモリ**: 最低1GB推奨
- **ディスク容量**: 最低10GB推奨
- **ネットワーク**: インターネット接続

## 🚀 クイックスタート

### 1. ローカル環境での実行

```bash
# リポジトリをクローン
git clone <repository-url>
cd HL_Data_Scraper

# Dockerイメージをビルド
docker-compose build

# アプリケーションを起動
docker-compose up -d

# ログを確認
docker-compose logs -f
```

### 2. EC2での自動デプロイ

```bash
# EC2インスタンスにSSH接続
ssh -i your-key.pem ec2-user@your-ec2-ip

# ファイルをアップロード（または直接クローン）
scp -i your-key.pem -r . ec2-user@your-ec2-ip:~/hyperliquid-scraper/

# デプロイスクリプトを実行
sudo bash deploy-ec2.sh
```

## 📁 ファイル構成

```
HL_Data_Scraper/
├── Dockerfile                 # メインDockerfile
├── docker-compose.yml         # Docker Composeサービス定義
├── docker-entrypoint.sh       # コンテナ起動スクリプト
├── healthcheck.py             # ヘルスチェックスクリプト
├── deploy-ec2.sh              # EC2自動デプロイスクリプト
├── .dockerignore              # Docker構築時の除外ファイル
├── requirements.txt           # Python依存関係
└── [アプリケーションファイル]
```

## 🔧 設定オプション

### Docker Compose環境変数

`docker-compose.yml`で以下の環境変数をカスタマイズできます：

```yaml
environment:
  - PYTHONUNBUFFERED=1          # Pythonバッファリング無効化
  - TZ=Asia/Tokyo               # タイムゾーン設定
  - SKIP_CONNECTION_TEST=false  # 起動時接続テスト（true=スキップ）
```

### ボリュームマウント

```yaml
volumes:
  - ./data:/app/data           # データ永続化
  - ./logs:/app/logs           # ログ永続化
```

### リソース制限

```yaml
deploy:
  resources:
    limits:
      memory: 512M             # メモリ上限
      cpus: '0.5'              # CPU上限
```

## 🏃 実行コマンド

### 基本操作

```bash
# サービス起動
docker-compose up -d

# サービス停止
docker-compose down

# サービス再起動
docker-compose restart

# ログ確認
docker-compose logs -f

# コンテナに入る
docker-compose exec hyperliquid-scraper bash
```

### 異なる通貨での実行

```bash
# ETHデータを収集
docker run --rm -v $(pwd)/data:/app/data hyperliquid-scraper python main.py --coin ETH

# テストネットで実行
docker run --rm -v $(pwd)/data:/app/data hyperliquid-scraper python main.py --testnet
```

## 📊 監視とヘルスチェック

### ヘルスチェック

Dockerコンテナは自動的にヘルスチェックを実行します：

```bash
# ヘルスチェック状態確認
docker-compose ps

# 手動ヘルスチェック実行
docker-compose exec hyperliquid-scraper python healthcheck.py
```

### ログ監視

```bash
# リアルタイムログ
docker-compose logs -f hyperliquid-scraper

# 最新100行のログ
docker-compose logs --tail=100 hyperliquid-scraper

# エラーログのみ
docker-compose logs hyperliquid-scraper | grep ERROR
```

## 🔍 トラブルシューティング

### よくある問題

#### 1. コンテナが起動しない

```bash
# コンテナ状態確認
docker-compose ps

# 詳細ログ確認
docker-compose logs hyperliquid-scraper

# コンテナ内でデバッグ
docker-compose run --rm hyperliquid-scraper bash
```

#### 2. データが保存されない

```bash
# ボリュームマウント確認
docker-compose exec hyperliquid-scraper ls -la /app/data

# 権限確認
docker-compose exec hyperliquid-scraper ls -la /app/data/
```

#### 3. メモリ不足

```bash
# リソース使用量確認
docker stats

# メモリ制限を増加（docker-compose.ymlを編集）
# memory: 1G に変更
```

#### 4. ネットワーク接続問題

```bash
# 接続テスト実行
docker-compose exec hyperliquid-scraper python test_connection.py

# DNS確認
docker-compose exec hyperliquid-scraper nslookup api.hyperliquid.xyz
```

## 🔧 カスタマイズ

### 異なる設定での実行

```bash
# カスタム設定ファイルをマウント
docker run -v /path/to/custom-config.py:/app/config.py hyperliquid-scraper

# 環境変数で設定を上書き
docker run -e COIN=ETH -e LOG_LEVEL=DEBUG hyperliquid-scraper
```

### 開発環境設定

```bash
# 開発用docker-compose.override.yml作成
version: '3.8'
services:
  hyperliquid-scraper:
    volumes:
      - .:/app  # ソースコードをマウント
    command: python main.py --log-level DEBUG
```

## 📈 本番環境での運用

### systemdサービスとして実行

EC2デプロイスクリプトを使用すると、自動的にsystemdサービスが作成されます：

```bash
# サービス状態確認
sudo systemctl status hyperliquid-data-scraper

# サービス開始/停止
sudo systemctl start hyperliquid-data-scraper
sudo systemctl stop hyperliquid-data-scraper

# ログ確認
sudo journalctl -u hyperliquid-data-scraper -f
```

### ログローテーション

自動的に設定されるログローテーション：

- **日次ローテーション**: 毎日ログファイルをローテーション
- **30日保持**: 30日分のログを保持
- **圧縮**: 古いログファイルを圧縮

### 監視設定

5分間隔でのヘルスチェック：

```bash
# 監視スクリプトログ確認
sudo tail -f /var/log/hyperliquid-data-scraper-monitor.log

# 手動監視実行
sudo /usr/local/bin/hyperliquid-data-scraper-monitor.sh
```

## 🔐 セキュリティ

### 推奨設定

1. **非rootユーザー**: コンテナ内では非rootユーザーで実行
2. **ファイアウォール**: 必要なポートのみ開放
3. **ログ制限**: ログファイルサイズの制限設定
4. **リソース制限**: CPU・メモリ使用量の制限

### セキュリティチェック

```bash
# コンテナのセキュリティスキャン
docker scan hyperliquid-scraper

# 実行ユーザー確認
docker-compose exec hyperliquid-scraper whoami
```

## 📞 サポート

### ログ収集

問題が発生した場合、以下の情報を収集してください：

```bash
# システム情報
docker --version
docker-compose --version

# コンテナ状態
docker-compose ps

# ログ（最新1000行）
docker-compose logs --tail=1000 hyperliquid-scraper > logs.txt

# ヘルスチェック結果
docker-compose exec hyperliquid-scraper python healthcheck.py
```

### よくある質問

**Q: データはどこに保存されますか？**
A: `./data/` ディレクトリにCSVファイルとして保存されます。

**Q: 別の通貨をスクレイピングできますか？**
A: はい、`--coin`パラメータで他の通貨を指定可能です。

**Q: EC2以外のクラウドでも動作しますか？**
A: はい、DockerとDocker Composeが動作する環境であれば使用可能です。

---

より詳細な情報については、メインの[README.md](README.md)をご覧ください。 