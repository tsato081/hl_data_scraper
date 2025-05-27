import asyncio
import logging
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import config
from websocket_client import HyperliquidWebSocketClient
from rest_client import HyperliquidRestClient
from csv_writer import CSVWriter
from s3_client import S3Client

class HyperliquidDataManager:
    """
    Hyperliquidデータ管理クラス
    WebSocketとREST APIからのデータを統合管理し、CSVファイルに書き込む
    """
    
    def __init__(self, coin: str = config.BTC_COIN, use_testnet: bool = False, use_s3: bool = None):
        self.coin = coin
        self.use_testnet = use_testnet
        self.logger = logging.getLogger(__name__)
        
        # クライアントとライター
        self.ws_client = HyperliquidWebSocketClient(
            use_testnet=use_testnet
        )
        self.rest_client = HyperliquidRestClient(
            base_url=config.TESTNET_HTTPS_BASE_URL if use_testnet else config.HTTPS_BASE_URL
        )
        self.csv_writer = CSVWriter()
        
        # S3クライアントの初期化
        self.use_s3 = config.USE_S3 if use_s3 is None else use_s3
        self.s3_client = None
        if self.use_s3:
            try:
                self.s3_client = S3Client()
                if not self.s3_client.is_available():
                    self.logger.warning("S3クライアントの初期化に失敗しました。S3機能は無効化されます。")
                    self.s3_client = None
            except Exception as e:
                self.logger.warning(f"S3クライアントの初期化中にエラーが発生しました: {e}")
                self.s3_client = None
        
        # 状態管理
        self.is_running = False
        self.last_funding_rate_update = 0
        self.last_open_interest_update = 0
        self.last_s3_upload = 0
        
        # データ一時保存
        self.latest_asset_context = None
        
        # スレッド管理
        self.rest_thread = None
        self.s3_thread = None
    
    async def start(self):
        """データ収集を開始"""
        if self.is_running:
            self.logger.warning("データ収集は既に実行中です")
            return
        
        self.is_running = True
        
        # WebSocket接続
        await self.ws_client.connect()
        
        # WebSocket購読を開始
        await self._start_websocket_subscriptions()
        
        # REST APIの定期実行スレッドを開始
        self.rest_thread = threading.Thread(target=self._rest_data_loop)
        self.rest_thread.daemon = True
        self.rest_thread.start()
        
        # S3アップロードスレッドを開始
        if self.use_s3 and self.s3_client and self.s3_client.is_available():
            self.s3_thread = threading.Thread(target=self._s3_upload_loop)
            self.s3_thread.daemon = True
            self.s3_thread.start()
        
        # ハートビートを開始
        asyncio.create_task(self.ws_client.heartbeat())
        
        self.logger.info(f"データ収集を開始しました: {self.coin}")
    
    async def stop(self):
        """データ収集を停止"""
        if not self.is_running:
            self.logger.warning("データ収集は既に停止しています")
            return
        
        self.is_running = False
        
        # WebSocket接続を切断
        if self.ws_client:
            await self.ws_client.disconnect()
        
        # REST APIセッションを閉じる
        if self.rest_client:
            self.rest_client.close()
        
        # スレッドの終了を待つ
        if self.rest_thread and self.rest_thread.is_alive():
            self.rest_thread.join(timeout=5)
        
        if self.s3_thread and self.s3_thread.is_alive():
            self.s3_thread.join(timeout=5)
        
        self.logger.info("データ収集を停止しました")
    
    async def _start_websocket_subscriptions(self):
        """WebSocket購読を開始"""
        # トレードデータ購読
        await self.ws_client.subscribe_trades(
            self.coin, 
            self._handle_trades_data
        )
        
        # 板情報購読
        await self.ws_client.subscribe_orderbook(
            self.coin, 
            self._handle_orderbook_data
        )
        
        # アセットコンテキスト購読
        await self.ws_client.subscribe_asset_context(
            self.coin, 
            self._handle_asset_context_data
        )
    
    def _rest_data_loop(self):
        """REST APIデータ取得ループ"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # ファンディングレートの定期取得
                if (current_time - self.last_funding_rate_update) >= config.FUNDING_RATE_UPDATE_INTERVAL:
                    self._fetch_funding_rate_data()
                    self.last_funding_rate_update = current_time
                
                # オープンインタレストの定期取得
                if (current_time - self.last_open_interest_update) >= config.OPEN_INTEREST_UPDATE_INTERVAL:
                    self._fetch_open_interest_data()
                    self.last_open_interest_update = current_time
                
                time.sleep(1)  # 1秒間隔でチェック
                
            except Exception as e:
                self.logger.error(f"REST APIデータ取得エラー: {e}")
                time.sleep(5)  # エラー時は5秒待機
    
    def _fetch_funding_rate_data(self):
        """ファンディングレートデータを取得"""
        try:
            # メタ情報とアセットコンテキストを取得
            meta_data = self.rest_client.get_perp_meta_and_asset_contexts()
            
            if meta_data and isinstance(meta_data, list) and len(meta_data) >= 2:
                asset_contexts = meta_data[1]  # アセットコンテキストは2番目の要素
                
                # BTC の情報を探す
                for asset_ctx in asset_contexts:
                    if asset_ctx.get('coin') == self.coin:
                        # WebSocketからのデータと重複を避けるため、少し違う形式で保存
                        funding_data = {
                            'coin': self.coin,
                            'ctx': asset_ctx.get('ctx', {})
                        }
                        self.csv_writer.write_funding_rate(funding_data)
                        break
                        
        except Exception as e:
            self.logger.error(f"ファンディングレート取得エラー: {e}")
    
    def _fetch_open_interest_data(self):
        """オープンインタレストデータを取得"""
        try:
            # メタ情報とアセットコンテキストを取得
            meta_data = self.rest_client.get_perp_meta_and_asset_contexts()
            
            if meta_data and isinstance(meta_data, list) and len(meta_data) >= 2:
                asset_contexts = meta_data[1]  # アセットコンテキストは2番目の要素
                
                # BTC の情報を探す
                for asset_ctx in asset_contexts:
                    if asset_ctx.get('coin') == self.coin:
                        # WebSocketからのデータと重複を避けるため、少し違う形式で保存
                        oi_data = {
                            'coin': self.coin,
                            'ctx': asset_ctx.get('ctx', {})
                        }
                        self.csv_writer.write_open_interest(oi_data)
                        break
                        
        except Exception as e:
            self.logger.error(f"オープンインタレスト取得エラー: {e}")
    
    def _s3_upload_loop(self):
        """S3への定期的なアップロード"""
        while self.is_running and self.use_s3 and self.s3_client and self.s3_client.is_available():
            try:
                current_time = time.time()
                
                # 定期的なアップロード
                if current_time - self.last_s3_upload >= config.S3_UPLOAD_INTERVAL:
                    # CSVファイルのパスを取得
                    file_paths = [
                        os.path.join(config.CSV_OUTPUT_DIR, filename)
                        for filename in config.CSV_FILES.values()
                    ]
                    
                    # ファイルをアップロード
                    self.s3_client.upload_multiple_files(file_paths)
                    
                    # 古いファイルを削除
                    self.s3_client.delete_old_files()
                    
                    self.last_s3_upload = current_time
                
                # 少し待機
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"S3アップロードループエラー: {e}")
                time.sleep(5)
    
    async def _handle_trades_data(self, channel: str, data: List[Dict]):
        """トレードデータ処理"""
        try:
            if isinstance(data, list) and data:
                # BTC取引のみフィルタリング
                btc_trades = [trade for trade in data if trade.get('coin') == self.coin]
                
                if btc_trades:
                    self.csv_writer.write_trades(btc_trades)
                    self.logger.debug(f"{len(btc_trades)}件のBTCトレードを記録しました")
                    
        except Exception as e:
            self.logger.error(f"トレードデータ処理エラー: {e}")
    
    async def _handle_orderbook_data(self, channel: str, data: Dict):
        """板情報データ処理"""
        try:
            if data.get('coin') == self.coin:
                self.csv_writer.write_orderbook(data)
                self.logger.debug(f"BTC板情報を記録しました")
                
        except Exception as e:
            self.logger.error(f"板情報データ処理エラー: {e}")
    
    async def _handle_asset_context_data(self, channel: str, data: Dict):
        """アセットコンテキストデータ処理"""
        try:
            if data.get('coin') == self.coin:
                self.latest_asset_context = data
                
                # ファンディングレートとオープンインタレストを記録
                self.csv_writer.write_funding_rate(data)
                self.csv_writer.write_open_interest(data)
                
                self.logger.debug(f"BTCアセットコンテキストを記録しました")
                
        except Exception as e:
            self.logger.error(f"アセットコンテキストデータ処理エラー: {e}")
    
    def get_status(self) -> Dict:
        """現在の状態を取得"""
        return {
            "is_running": self.is_running,
            "coin": self.coin,
            "use_testnet": self.use_testnet,
            "websocket_connected": self.ws_client.is_connected if self.ws_client else False,
            "s3_available": self.s3_client.is_available() if self.s3_client else False,
            "last_funding_rate_update": datetime.fromtimestamp(self.last_funding_rate_update).isoformat() if self.last_funding_rate_update else None,
            "last_open_interest_update": datetime.fromtimestamp(self.last_open_interest_update).isoformat() if self.last_open_interest_update else None,
            "last_s3_upload": datetime.fromtimestamp(self.last_s3_upload).isoformat() if self.last_s3_upload else None,
            "csv_stats": self.csv_writer.get_file_stats(),
            "s3_stats": self.s3_client.get_upload_statistics() if self.s3_client else None,
            "latest_asset_context": self.latest_asset_context
        }
    
    def backup_data(self):
        """データをバックアップ"""
        try:
            self.csv_writer.backup_files()
            self.logger.info("データバックアップが完了しました")
        except Exception as e:
            self.logger.error(f"データバックアップエラー: {e}")
    
    async def run_forever(self):
        """永続的にデータ収集を実行"""
        while True:
            try:
                await self.start()
                
                # 実行継続のための待機
                while self.is_running:
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                self.logger.info("ユーザーにより停止されました")
                break
            except Exception as e:
                self.logger.error(f"予期しないエラー: {e}")
                await self.stop()
                
                # 再接続前に少し待機
                self.logger.info("10秒後に再接続を試みます...")
                await asyncio.sleep(10) 