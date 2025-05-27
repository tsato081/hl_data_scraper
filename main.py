#!/usr/bin/env python3
"""
Hyperliquid Data Scraper
BTCパーペチュアル契約のトレード、板情報、ファンディングレート、オープンインタレストを
リアルタイムで取得し、CSVファイルに保存するアプリケーション
"""

import asyncio
import logging
import signal
import sys
import argparse
from datetime import datetime
import config
from data_manager import HyperliquidDataManager

class HyperliquidDataScraper:
    """
    Hyperliquidデータスクレイパーメインクラス
    """
    
    def __init__(self, coin: str = config.BTC_COIN, testnet: bool = False, use_s3: bool = None):
        self.coin = coin
        self.testnet = testnet
        self.use_s3 = use_s3 if use_s3 is not None else config.USE_S3
        self.data_manager = None
        self.is_running = False
        
        # ログ設定
        self._setup_logging()
        
        # シグナルハンドラー設定
        self._setup_signal_handlers()
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_logging(self):
        """ログ設定を初期化"""
        # ログレベル設定
        log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        
        # ログフォーマット
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        # ファイルハンドラー
        file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # ルートロガー設定
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    def _setup_signal_handlers(self):
        """シグナルハンドラーを設定"""
        def signal_handler(signum, frame):
            """シグナル受信時の処理"""
            logger = logging.getLogger(__name__)
            logger.info(f"シグナル {signum} を受信しました。アプリケーションを停止します...")
            self.is_running = False
        
        # SIGINT (Ctrl+C) と SIGTERM の処理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """アプリケーションを開始"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("Hyperliquid Data Scraper を開始します")
            self.logger.info(f"対象通貨: {self.coin}")
            self.logger.info(f"テストネット: {'有効' if self.testnet else '無効'}")
            self.logger.info(f"S3ストレージ: {'有効' if self.use_s3 else '無効'}")
            if self.use_s3:
                self.logger.info(f"S3バケット: {config.S3_BUCKET_NAME}")
                self.logger.info(f"S3リージョン: {config.S3_REGION}")
            self.logger.info(f"開始時刻: {datetime.now().isoformat()}")
            self.logger.info("=" * 60)
            
            # データマネージャーを初期化
            self.data_manager = HyperliquidDataManager(
                coin=self.coin,
                use_testnet=self.testnet
            )
            self.is_running = True
            
            # データ収集を開始
            await self.data_manager.start()
            
            # メインループ
            await self._main_loop()
            
        except Exception as e:
            self.logger.error(f"アプリケーション開始エラー: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """アプリケーションを停止"""
        self.logger.info("アプリケーションを停止しています...")
        self.is_running = False
        
        if self.data_manager:
            await self.data_manager.stop()
        
        self.logger.info("アプリケーションが正常に停止しました")
    
    async def _main_loop(self):
        """メインループ"""
        status_interval = 300  # 5分間隔でステータス出力
        last_status_time = 0
        
        while self.is_running:
            try:
                current_time = asyncio.get_event_loop().time()
                
                # 定期的にステータスを出力
                if current_time - last_status_time >= status_interval:
                    await self._print_status()
                    last_status_time = current_time
                
                # 短い間隔で待機
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"メインループエラー: {e}")
                await asyncio.sleep(5)
    
    async def _print_status(self):
        """ステータス情報を出力"""
        try:
            if self.data_manager:
                status = self.data_manager.get_status()
                
                self.logger.info("=" * 50)
                self.logger.info("アプリケーションステータス")
                self.logger.info(f"実行状態: {'実行中' if status['is_running'] else '停止'}")
                self.logger.info(f"WebSocket接続: {'接続' if status['websocket_connected'] else '切断'}")
                self.logger.info(f"対象通貨: {status['coin']}")
                
                # S3ステータス
                if self.use_s3:
                    s3_stats = status.get('s3_stats', {})
                    if s3_stats.get('available', False):
                        self.logger.info("S3ストレージ:")
                        self.logger.info(f"  バケット: {s3_stats.get('bucket_name', 'N/A')}")
                        self.logger.info(f"  総ファイル数: {s3_stats.get('total_files', 0):,}")
                        self.logger.info(f"  総容量: {s3_stats.get('total_size_bytes', 0):,}バイト")
                        if s3_stats.get('latest_file'):
                            self.logger.info(f"  最新ファイル: {s3_stats['latest_file']['key']}")
                            self.logger.info(f"  最終更新: {s3_stats['latest_file']['last_modified']}")
                    else:
                        self.logger.warning(f"S3ストレージ: 利用不可 ({s3_stats.get('error', '不明なエラー')})")
                
                # CSVファイル統計
                csv_stats = status.get('csv_stats', {})
                self.logger.info("CSVファイル統計:")
                for data_type, stats in csv_stats.items():
                    if stats.get('exists', True):
                        row_count = stats.get('row_count', 0)
                        file_size = stats.get('file_size_bytes', 0)
                        self.logger.info(f"  {data_type}: {row_count:,}行, {file_size:,}バイト")
                
                # 最新のアセットコンテキスト
                if status.get('latest_asset_context'):
                    ctx = status['latest_asset_context'].get('ctx', {})
                    self.logger.info(f"最新価格情報:")
                    self.logger.info(f"  マーク価格: {ctx.get('markPx', 'N/A')}")
                    self.logger.info(f"  ファンディングレート: {ctx.get('funding', 'N/A')}")
                    self.logger.info(f"  オープンインタレスト: {ctx.get('openInterest', 'N/A')}")
                
                self.logger.info("=" * 50)
                
        except Exception as e:
            self.logger.error(f"ステータス出力エラー: {e}")


def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description="Hyperliquid Data Scraper - BTCパーペチュアルデータ収集ツール"
    )
    
    parser.add_argument(
        "--coin", "-c",
        default=config.BTC_COIN,
        help=f"対象通貨シンボル (デフォルト: {config.BTC_COIN})"
    )
    
    parser.add_argument(
        "--testnet", "-t",
        action="store_true",
        help="テストネットを使用する"
    )
    
    parser.add_argument(
        "--s3", "-s",
        action="store_true",
        help="S3ストレージを使用する"
    )
    
    parser.add_argument(
        "--no-s3",
        action="store_true",
        help="S3ストレージを使用しない"
    )
    
    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=config.LOG_LEVEL,
        help=f"ログレベル (デフォルト: {config.LOG_LEVEL})"
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Hyperliquid Data Scraper 1.0.0"
    )
    
    return parser.parse_args()


async def main():
    """メイン関数"""
    try:
        # コマンドライン引数を解析
        args = parse_arguments()
        
        # ログレベルを更新
        config.LOG_LEVEL = args.log_level
        
        # S3使用設定を更新
        use_s3 = None
        if args.s3:
            use_s3 = True
        elif args.no_s3:
            use_s3 = False
        
        # アプリケーションを作成・実行
        scraper = HyperliquidDataScraper(
            coin=args.coin,
            testnet=args.testnet,
            use_s3=use_s3
        )
        
        await scraper.start()
        
    except KeyboardInterrupt:
        print("\nユーザーによる停止要求を受信しました")
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Windowsでのevent loopポリシー設定
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # メイン関数を実行
    asyncio.run(main()) 