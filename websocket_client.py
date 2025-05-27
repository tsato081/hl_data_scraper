import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Dict, List, Optional, Callable
import config

class HyperliquidWebSocketClient:
    """
    HyperliquidのWebSocket APIクライアント
    """
    
    def __init__(self, url: str = config.WEBSOCKET_URL):
        self.url = url
        self.websocket = None
        self.subscriptions = {}
        self.callbacks = {}
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """WebSocket接続を確立"""
        try:
            self.websocket = await websockets.connect(self.url)
            self.is_connected = True
            self.logger.info(f"WebSocketに接続しました: {self.url}")
            
            # メッセージ受信のタスクを開始
            asyncio.create_task(self._listen_messages())
            
        except Exception as e:
            self.logger.error(f"WebSocket接続エラー: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """WebSocket接続を切断"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self.logger.info("WebSocket接続を切断しました")
    
    async def subscribe_trades(self, coin: str, callback: Callable):
        """
        トレードデータを購読
        
        Args:
            coin: 通貨シンボル (例: "BTC")
            callback: データ受信時のコールバック関数
        """
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "trades",
                "coin": coin
            }
        }
        
        await self._subscribe(f"trades_{coin}", subscription, callback)
    
    async def subscribe_orderbook(self, coin: str, callback: Callable):
        """
        板情報を購読
        
        Args:
            coin: 通貨シンボル (例: "BTC")
            callback: データ受信時のコールバック関数
        """
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": coin
            }
        }
        
        await self._subscribe(f"l2Book_{coin}", subscription, callback)
    
    async def subscribe_asset_context(self, coin: str, callback: Callable):
        """
        アセットコンテキスト（ファンディングレート、オープンインタレスト等）を購読
        
        Args:
            coin: 通貨シンボル (例: "BTC")
            callback: データ受信時のコールバック関数
        """
        subscription = {
            "method": "subscribe",
            "subscription": {
                "type": "activeAssetCtx",
                "coin": coin
            }
        }
        
        await self._subscribe(f"activeAssetCtx_{coin}", subscription, callback)
    
    async def _subscribe(self, key: str, subscription: Dict, callback: Callable):
        """
        内部購読メソッド
        
        Args:
            key: 購読キー
            subscription: 購読メッセージ
            callback: コールバック関数
        """
        if not self.is_connected:
            raise Exception("WebSocket接続が確立されていません")
        
        try:
            await self.websocket.send(json.dumps(subscription))
            self.subscriptions[key] = subscription
            self.callbacks[key] = callback
            self.logger.info(f"購読を開始しました: {key}")
            
        except Exception as e:
            self.logger.error(f"購読エラー {key}: {e}")
            raise
    
    async def _listen_messages(self):
        """WebSocketメッセージを受信"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSONデコードエラー: {e}")
                except Exception as e:
                    self.logger.error(f"メッセージ処理エラー: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket接続が切断されました")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"メッセージ受信エラー: {e}")
            self.is_connected = False
    
    async def _handle_message(self, data: Dict):
        """受信メッセージの処理"""
        channel = data.get("channel")
        
        if channel == "subscriptionResponse":
            # 購読確認メッセージ
            subscription_type = data.get("data", {}).get("subscription", {}).get("type")
            coin = data.get("data", {}).get("subscription", {}).get("coin", "")
            self.logger.info(f"購読確認: {subscription_type} for {coin}")
            
        elif channel in ["trades", "l2Book", "activeAssetCtx"]:
            # データメッセージ
            await self._process_data_message(channel, data)
            
        else:
            self.logger.debug(f"未知のチャネル: {channel}")
    
    async def _process_data_message(self, channel: str, data: Dict):
        """データメッセージの処理"""
        message_data = data.get("data", {})
        
        if channel == "trades":
            # トレードデータの処理
            for callback_key, callback in self.callbacks.items():
                if callback_key.startswith("trades_"):
                    await self._safe_callback(callback, channel, message_data)
                    
        elif channel == "l2Book":
            # 板情報の処理
            for callback_key, callback in self.callbacks.items():
                if callback_key.startswith("l2Book_"):
                    await self._safe_callback(callback, channel, message_data)
                    
        elif channel == "activeAssetCtx":
            # アセットコンテキストの処理
            for callback_key, callback in self.callbacks.items():
                if callback_key.startswith("activeAssetCtx_"):
                    await self._safe_callback(callback, channel, message_data)
    
    async def _safe_callback(self, callback: Callable, channel: str, data: Dict):
        """コールバック関数の安全な実行"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(channel, data)
            else:
                callback(channel, data)
        except Exception as e:
            self.logger.error(f"コールバック実行エラー: {e}")
    
    async def heartbeat(self):
        """ハートビート送信"""
        while self.is_connected:
            try:
                if self.websocket:
                    ping_message = {"method": "ping"}
                    await self.websocket.send(json.dumps(ping_message))
                    self.logger.debug("ハートビートを送信しました")
                
                await asyncio.sleep(config.HEARTBEAT_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"ハートビートエラー: {e}")
                break 