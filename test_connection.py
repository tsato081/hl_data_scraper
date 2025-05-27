#!/usr/bin/env python3
"""
Hyperliquid API接続テストスクリプト
"""

import asyncio
import json
import logging
from rest_client import HyperliquidRestClient
from websocket_client import HyperliquidWebSocketClient
import config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_rest_api():
    """REST API接続テスト"""
    logger.info("=== REST API接続テスト ===")
    
    client = HyperliquidRestClient()
    
    try:
        # 全通貨の中間価格を取得
        logger.info("全通貨のミッド価格を取得中...")
        mids = client.get_all_mids()
        
        if mids:
            logger.info(f"取得成功: {len(mids)}通貨のデータを取得")
            
            # BTCの価格を表示
            if config.BTC_COIN in mids:
                btc_price = mids[config.BTC_COIN]
                logger.info(f"BTC価格: ${btc_price}")
            else:
                logger.warning(f"{config.BTC_COIN}の価格が見つかりません")
                # 利用可能な通貨の一部を表示
                available_coins = list(mids.keys())[:5]
                logger.info(f"利用可能な通貨例: {available_coins}")
        else:
            logger.error("データの取得に失敗しました")
        
        # BTCの板情報を取得
        logger.info(f"{config.BTC_COIN}の板情報を取得中...")
        orderbook = client.get_l2_book(config.BTC_COIN)
        
        if orderbook and len(orderbook) >= 2:
            bids = orderbook[0]  # 買い注文
            asks = orderbook[1]  # 売り注文
            
            if bids and asks:
                best_bid = bids[0] if bids else None
                best_ask = asks[0] if asks else None
                
                logger.info(f"最良買い注文: {best_bid}")
                logger.info(f"最良売り注文: {best_ask}")
                
                if best_bid and best_ask:
                    spread = float(best_ask['px']) - float(best_bid['px'])
                    logger.info(f"スプレッド: ${spread:.2f}")
            else:
                logger.warning("板情報が空です")
        else:
            logger.error("板情報の取得に失敗しました")
        
        # メタ情報を取得
        logger.info("パーペチュアル契約の情報を取得中...")
        meta_data = client.get_perp_meta_and_asset_contexts()
        
        if meta_data and isinstance(meta_data, list) and len(meta_data) >= 2:
            meta_info = meta_data[0]
            asset_contexts = meta_data[1]
            
            logger.info(f"メタ情報取得成功: {len(asset_contexts)}通貨のコンテキスト情報")
            
            # BTCの詳細情報を表示
            for asset_ctx in asset_contexts:
                if asset_ctx.get('coin') == config.BTC_COIN:
                    ctx = asset_ctx.get('ctx', {})
                    logger.info(f"BTC詳細情報:")
                    logger.info(f"  マーク価格: ${ctx.get('markPx', 'N/A')}")
                    logger.info(f"  オラクル価格: ${ctx.get('oraclePx', 'N/A')}")
                    logger.info(f"  ファンディングレート: {ctx.get('funding', 'N/A')}")
                    logger.info(f"  オープンインタレスト: {ctx.get('openInterest', 'N/A')}")
                    break
        else:
            logger.error("メタ情報の取得に失敗しました")
            
    except Exception as e:
        logger.error(f"REST APIテストエラー: {e}")
    
    finally:
        client.close()
    
    logger.info("=== REST APIテスト完了 ===\n")

async def test_websocket_api():
    """WebSocket API接続テスト"""
    logger.info("=== WebSocket API接続テスト ===")
    
    client = HyperliquidWebSocketClient()
    test_duration = 10  # 10秒間テスト
    
    # データ受信カウンター
    counters = {
        'trades': 0,
        'orderbook': 0,
        'asset_context': 0
    }
    
    async def trade_callback(channel, data):
        """トレードデータコールバック"""
        if isinstance(data, list):
            counters['trades'] += len(data)
            if data:
                latest_trade = data[-1]
                logger.info(f"トレード受信: {latest_trade.get('coin')} - 価格: ${latest_trade.get('px')}, 数量: {latest_trade.get('sz')}")
    
    async def orderbook_callback(channel, data):
        """板情報コールバック"""
        counters['orderbook'] += 1
        coin = data.get('coin')
        levels = data.get('levels', [[], []])
        bids = levels[0] if len(levels) > 0 else []
        asks = levels[1] if len(levels) > 1 else []
        
        best_bid_price = bids[0]['px'] if bids else 'N/A'
        best_ask_price = asks[0]['px'] if asks else 'N/A'
        
        logger.info(f"板情報受信: {coin} - Best Bid: ${best_bid_price}, Best Ask: ${best_ask_price}")
    
    async def asset_context_callback(channel, data):
        """アセットコンテキストコールバック"""
        counters['asset_context'] += 1
        coin = data.get('coin')
        ctx = data.get('ctx', {})
        
        logger.info(f"アセットコンテキスト受信: {coin} - マーク価格: ${ctx.get('markPx')}, ファンディング: {ctx.get('funding')}")
    
    try:
        # WebSocket接続
        await client.connect()
        logger.info("WebSocket接続成功")
        
        # 購読開始
        await client.subscribe_trades(config.BTC_COIN, trade_callback)
        await client.subscribe_orderbook(config.BTC_COIN, orderbook_callback)
        await client.subscribe_asset_context(config.BTC_COIN, asset_context_callback)
        
        logger.info(f"{test_duration}秒間データを受信します...")
        
        # テスト実行
        await asyncio.sleep(test_duration)
        
        # 結果表示
        logger.info("=== 受信データ統計 ===")
        logger.info(f"トレードデータ: {counters['trades']}件")
        logger.info(f"板情報更新: {counters['orderbook']}回")
        logger.info(f"アセットコンテキスト更新: {counters['asset_context']}回")
        
        if sum(counters.values()) > 0:
            logger.info("WebSocketデータ受信テスト成功!")
        else:
            logger.warning("データが受信されませんでした")
    
    except Exception as e:
        logger.error(f"WebSocketテストエラー: {e}")
    
    finally:
        await client.disconnect()
    
    logger.info("=== WebSocketテスト完了 ===\n")

async def main():
    """メインテスト関数"""
    logger.info("Hyperliquid API接続テストを開始します")
    logger.info(f"対象通貨: {config.BTC_COIN}")
    logger.info(f"WebSocket URL: {config.WEBSOCKET_URL}")
    logger.info(f"REST API URL: {config.HTTPS_BASE_URL}")
    print("")
    
    try:
        # REST APIテスト
        await test_rest_api()
        
        # WebSocketテスト
        await test_websocket_api()
        
        logger.info("全てのテストが完了しました")
        
    except KeyboardInterrupt:
        logger.info("ユーザーによりテストが停止されました")
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")

if __name__ == "__main__":
    asyncio.run(main())