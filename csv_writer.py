import csv
import os
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import config

class CSVWriter:
    """
    CSVファイル書き込み管理クラス
    """
    
    def __init__(self, output_dir: str = config.CSV_OUTPUT_DIR):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
        # 出力ディレクトリを作成
        self._ensure_output_directory()
        
        # CSVファイルパス
        self.file_paths = {
            data_type: os.path.join(self.output_dir, filename)
            for data_type, filename in config.CSV_FILES.items()
        }
        
        # CSVヘッダーを初期化
        self._initialize_csv_files()
    
    def _ensure_output_directory(self):
        """出力ディレクトリが存在することを確認"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"出力ディレクトリを作成しました: {self.output_dir}")
    
    def _initialize_csv_files(self):
        """CSVファイルを初期化（ヘッダー行を書き込み）"""
        headers = {
            "trades": config.TRADES_COLUMNS,
            "orderbook": config.ORDERBOOK_COLUMNS,
            "funding_rate": config.FUNDING_RATE_COLUMNS,
            "open_interest": config.OPEN_INTEREST_COLUMNS
        }
        
        for data_type, columns in headers.items():
            file_path = self.file_paths[data_type]
            
            # ファイルが存在しない場合のみヘッダーを書き込み
            if not os.path.exists(file_path):
                try:
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(columns)
                    self.logger.info(f"CSVファイルを初期化しました: {file_path}")
                except Exception as e:
                    self.logger.error(f"CSVファイル初期化エラー {file_path}: {e}")
    
    def write_trades(self, trades_data: List[Dict]):
        """
        トレードデータをCSVに書き込み
        
        Args:
            trades_data: トレードデータのリスト
        """
        if not trades_data:
            return
        
        rows = []
        for trade in trades_data:
            row = [
                datetime.fromtimestamp(trade.get('time', 0) / 1000).isoformat(),  # timestamp
                trade.get('coin', ''),  # coin
                trade.get('side', ''),  # side
                trade.get('px', ''),   # price
                trade.get('sz', ''),   # size
                trade.get('tid', ''),  # trade_id
                trade.get('users', ['', ''])[0] if len(trade.get('users', [])) > 0 else '',  # buyer
                trade.get('users', ['', ''])[1] if len(trade.get('users', [])) > 1 else '',  # seller
                trade.get('hash', ''), # hash
                'true' if trade.get('crossed', False) else 'false',  # crossed
                ''  # fee (WebSocketからは取得できない場合がある)
            ]
            rows.append(row)
        
        self._write_to_csv("trades", rows)
    
    def write_orderbook(self, orderbook_data: Dict):
        """
        板情報をCSVに書き込み
        
        Args:
            orderbook_data: 板情報データ
        """
        if not orderbook_data:
            return
        
        timestamp = datetime.fromtimestamp(orderbook_data.get('time', 0) / 1000).isoformat()
        coin = orderbook_data.get('coin', '')
        levels = orderbook_data.get('levels', [[], []])
        
        # ビッド（買い注文）とアスク（売り注文）
        bids = levels[0] if len(levels) > 0 else []
        asks = levels[1] if len(levels) > 1 else []
        
        # 最良価格を取得
        best_bid = bids[0] if bids else {'px': '', 'sz': ''}
        best_ask = asks[0] if asks else {'px': '', 'sz': ''}
        
        # スプレッドを計算
        spread = ''
        if best_bid.get('px') and best_ask.get('px'):
            try:
                spread = str(float(best_ask['px']) - float(best_bid['px']))
            except (ValueError, TypeError):
                spread = ''
        
        row = [
            timestamp,
            coin,
            str(bids),  # bids (JSON文字列として保存)
            str(asks),  # asks (JSON文字列として保存)
            best_bid.get('px', ''),   # bid_price
            best_ask.get('px', ''),   # ask_price
            best_bid.get('sz', ''),   # bid_size
            best_ask.get('sz', ''),   # ask_size
            spread  # spread
        ]
        
        self._write_to_csv("orderbook", [row])
    
    def write_funding_rate(self, asset_ctx_data: Dict):
        """
        ファンディングレートをCSVに書き込み
        
        Args:
            asset_ctx_data: アセットコンテキストデータ
        """
        if not asset_ctx_data:
            return
        
        coin = asset_ctx_data.get('coin', '')
        ctx = asset_ctx_data.get('ctx', {})
        
        # ファンディングレート情報
        funding_rate = ctx.get('funding', '')
        mark_price = ctx.get('markPx', '')
        oracle_price = ctx.get('oraclePx', '')
        
        row = [
            datetime.now().isoformat(),  # timestamp
            coin,  # coin
            funding_rate,  # funding_rate
            '',  # predicted_funding_rate (取得できない場合は空)
            '',  # funding_time (取得できない場合は空)
            mark_price,  # mark_price
            oracle_price  # index_price (oraclePxを使用)
        ]
        
        self._write_to_csv("funding_rate", [row])
    
    def write_open_interest(self, asset_ctx_data: Dict):
        """
        オープンインタレストをCSVに書き込み
        
        Args:
            asset_ctx_data: アセットコンテキストデータ
        """
        if not asset_ctx_data:
            return
        
        coin = asset_ctx_data.get('coin', '')
        ctx = asset_ctx_data.get('ctx', {})
        
        # オープンインタレスト情報
        open_interest = ctx.get('openInterest', '')
        mark_price = ctx.get('markPx', '')
        oracle_price = ctx.get('oraclePx', '')
        
        row = [
            datetime.now().isoformat(),  # timestamp
            coin,  # coin
            open_interest,  # open_interest
            mark_price,  # mark_price
            oracle_price  # oracle_price
        ]
        
        self._write_to_csv("open_interest", [row])
    
    def _write_to_csv(self, data_type: str, rows: List[List]):
        """
        CSVファイルに行を書き込み
        
        Args:
            data_type: データタイプ ("trades", "orderbook", "funding_rate", "open_interest")
            rows: 書き込む行のリスト
        """
        if not rows:
            return
        
        file_path = self.file_paths.get(data_type)
        if not file_path:
            self.logger.error(f"不明なデータタイプ: {data_type}")
            return
        
        with self.lock:
            try:
                with open(file_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
                
                self.logger.debug(f"{data_type}データを{len(rows)}行書き込みました: {file_path}")
                
            except Exception as e:
                self.logger.error(f"CSV書き込みエラー {file_path}: {e}")
    
    def get_file_stats(self) -> Dict[str, Dict]:
        """
        各CSVファイルの統計情報を取得
        
        Returns:
            Dict: ファイル統計情報
        """
        stats = {}
        
        for data_type, file_path in self.file_paths.items():
            try:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    
                    # 行数を数える
                    with open(file_path, 'r', encoding='utf-8') as f:
                        row_count = sum(1 for _ in f) - 1  # ヘッダー行を除く
                    
                    modification_time = datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    ).isoformat()
                    
                    stats[data_type] = {
                        "file_path": file_path,
                        "file_size_bytes": file_size,
                        "row_count": row_count,
                        "last_modified": modification_time
                    }
                else:
                    stats[data_type] = {
                        "file_path": file_path,
                        "exists": False
                    }
                    
            except Exception as e:
                self.logger.error(f"ファイル統計取得エラー {file_path}: {e}")
                stats[data_type] = {
                    "file_path": file_path,
                    "error": str(e)
                }
        
        return stats
    
    def backup_files(self, backup_suffix: str = None):
        """
        CSVファイルをバックアップ
        
        Args:
            backup_suffix: バックアップファイルの接尾辞
        """
        if backup_suffix is None:
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for data_type, file_path in self.file_paths.items():
            if os.path.exists(file_path):
                try:
                    backup_path = f"{file_path}.backup_{backup_suffix}"
                    import shutil
                    shutil.copy2(file_path, backup_path)
                    self.logger.info(f"ファイルをバックアップしました: {backup_path}")
                except Exception as e:
                    self.logger.error(f"バックアップエラー {file_path}: {e}") 