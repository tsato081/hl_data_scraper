import requests
import json
import logging
from typing import Dict, List, Optional
import config

class HyperliquidRestClient:
    """
    HyperliquidのREST APIクライアント
    """
    
    def __init__(self, base_url: str = config.HTTPS_BASE_URL):
        self.base_url = base_url
        self.info_url = f"{base_url}/info"
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        # セッションの設定
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "HyperliquidDataScraper/1.0"
        })
    
    def get_all_mids(self) -> Optional[Dict]:
        """
        全通貨のミッド価格を取得
        
        Returns:
            Dict: 全通貨のミッド価格辞書
        """
        payload = {
            "type": "allMids"
        }
        
        return self._make_request(payload)
    
    def get_l2_book(self, coin: str, n_sig_figs: Optional[int] = None) -> Optional[Dict]:
        """
        指定通貨の板情報を取得
        
        Args:
            coin: 通貨シンボル (例: "BTC")
            n_sig_figs: 有効桁数 (2, 3, 4, 5, またはNone)
            
        Returns:
            Dict: 板情報
        """
        payload = {
            "type": "l2Book",
            "coin": coin
        }
        
        if n_sig_figs is not None:
            payload["nSigFigs"] = n_sig_figs
        
        return self._make_request(payload)
    
    def get_meta_info(self) -> Optional[Dict]:
        """
        メタ情報を取得（通貨一覧、ファンディング情報等）
        
        Returns:
            Dict: メタ情報
        """
        payload = {
            "type": "meta"
        }
        
        return self._make_request(payload)
    
    def get_perp_meta_and_asset_contexts(self) -> Optional[Dict]:
        """
        パーペチュアル契約のメタ情報とアセットコンテキストを取得
        
        Returns:
            Dict: パーペチュアル契約情報
        """
        payload = {
            "type": "metaAndAssetCtxs"
        }
        
        return self._make_request(payload)
    
    def get_funding_history(self, coin: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> Optional[List]:
        """
        ファンディング履歴を取得
        
        Args:
            coin: 通貨シンボル (例: "BTC")
            start_time: 開始時刻 (milliseconds)
            end_time: 終了時刻 (milliseconds)
            
        Returns:
            List: ファンディング履歴
        """
        payload = {
            "type": "fundingHistory",
            "coin": coin
        }
        
        if start_time is not None:
            payload["startTime"] = start_time
        if end_time is not None:
            payload["endTime"] = end_time
        
        return self._make_request(payload)
    
    def get_candle_snapshot(self, coin: str, interval: str, start_time: int, end_time: int) -> Optional[List]:
        """
        キャンドルスティックデータを取得
        
        Args:
            coin: 通貨シンボル (例: "BTC")
            interval: 時間間隔 (例: "1m", "5m", "15m", "1h", "1d")
            start_time: 開始時刻 (milliseconds)
            end_time: 終了時刻 (milliseconds)
            
        Returns:
            List: キャンドルスティックデータ
        """
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_time,
                "endTime": end_time
            }
        }
        
        return self._make_request(payload)
    
    def get_user_state(self, user: str) -> Optional[Dict]:
        """
        ユーザーの状態を取得
        
        Args:
            user: ユーザーアドレス
            
        Returns:
            Dict: ユーザー状態
        """
        payload = {
            "type": "clearinghouseState",
            "user": user
        }
        
        return self._make_request(payload)
    
    def get_open_orders(self, user: str) -> Optional[List]:
        """
        ユーザーのオープンオーダーを取得
        
        Args:
            user: ユーザーアドレス
            
        Returns:
            List: オープンオーダー一覧
        """
        payload = {
            "type": "openOrders",
            "user": user
        }
        
        return self._make_request(payload)
    
    def get_user_fills(self, user: str, aggregate_by_time: bool = False) -> Optional[List]:
        """
        ユーザーの約定履歴を取得
        
        Args:
            user: ユーザーアドレス
            aggregate_by_time: 時間で集約するかどうか
            
        Returns:
            List: 約定履歴
        """
        payload = {
            "type": "userFills",
            "user": user
        }
        
        if aggregate_by_time:
            payload["aggregateByTime"] = True
        
        return self._make_request(payload)
    
    def _make_request(self, payload: Dict) -> Optional[Dict]:
        """
        API リクエストを実行
        
        Args:
            payload: リクエストペイロード
            
        Returns:
            レスポンスデータまたはNone
        """
        try:
            self.logger.debug(f"API リクエスト: {payload}")
            
            response = self.session.post(
                self.info_url,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"API レスポンス受信: {len(str(data))} bytes")
            
            return data
            
        except requests.exceptions.Timeout:
            self.logger.error("APIリクエストがタイムアウトしました")
            return None
            
        except requests.exceptions.ConnectionError:
            self.logger.error("API接続エラーが発生しました")
            return None
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTPエラー: {e}")
            return None
            
        except json.JSONDecodeError:
            self.logger.error("APIレスポンスのJSONデコードに失敗しました")
            return None
            
        except Exception as e:
            self.logger.error(f"予期しないAPIエラー: {e}")
            return None
    
    def close(self):
        """セッションを閉じる"""
        if self.session:
            self.session.close()
            self.logger.info("REST APIセッションを閉じました") 