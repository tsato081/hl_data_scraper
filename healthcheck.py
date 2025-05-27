#!/usr/bin/env python3
"""
Hyperliquid Data Scraper ヘルスチェックスクリプト
Dockerコンテナの健全性を監視する
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta

def check_csv_files():
    """CSVファイルの存在と更新状況をチェック"""
    data_dir = "data"
    csv_files = [
        "btc_trades.csv",
        "btc_orderbook.csv", 
        "btc_funding_rate.csv",
        "btc_open_interest.csv"
    ]
    
    current_time = time.time()
    max_age = 300  # 5分以内に更新されているかチェック
    
    for csv_file in csv_files:
        file_path = os.path.join(data_dir, csv_file)
        
        # ファイルの存在チェック
        if not os.path.exists(file_path):
            print(f"ERROR: {csv_file} が存在しません")
            return False
        
        # ファイルサイズチェック（ヘッダーのみでないか）
        file_size = os.path.getsize(file_path)
        if file_size < 100:  # 100バイト以下の場合はデータがない
            print(f"WARNING: {csv_file} のサイズが小さすぎます ({file_size} bytes)")
            continue
        
        # 最終更新時刻チェック
        last_modified = os.path.getmtime(file_path)
        age = current_time - last_modified
        
        if age > max_age:
            print(f"WARNING: {csv_file} が {age:.0f}秒前から更新されていません")
        else:
            print(f"OK: {csv_file} は正常に更新されています")
    
    return True

def check_log_file():
    """ログファイルをチェック"""
    log_file = "hyperliquid_scraper.log"
    
    if not os.path.exists(log_file):
        print(f"WARNING: ログファイル {log_file} が存在しません")
        return True  # ログファイルは必須ではない
    
    # 最近のエラーログをチェック
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 最新100行をチェック
        recent_lines = lines[-100:] if len(lines) > 100 else lines
        error_count = 0
        
        for line in recent_lines:
            if "ERROR" in line or "CRITICAL" in line:
                error_count += 1
        
        if error_count > 10:  # 最近100行で10個以上のエラーがある場合
            print(f"WARNING: 多数のエラーログが検出されました ({error_count}個)")
            return False
        
        print(f"OK: ログファイルは正常です (最近のエラー: {error_count}個)")
        return True
        
    except Exception as e:
        print(f"WARNING: ログファイルの読み取りに失敗しました: {e}")
        return True

def check_process_health():
    """プロセスの健全性をチェック"""
    try:
        # メモリ使用量チェック（簡易版）
        import psutil
        
        current_process = psutil.Process()
        memory_info = current_process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # メモリ使用量が400MB以上の場合は警告
        if memory_mb > 400:
            print(f"WARNING: メモリ使用量が高くなっています ({memory_mb:.1f}MB)")
        else:
            print(f"OK: メモリ使用量は正常です ({memory_mb:.1f}MB)")
        
        return True
        
    except ImportError:
        # psutilがない場合はスキップ
        print("INFO: psutilが利用できないため、プロセスチェックをスキップします")
        return True
    except Exception as e:
        print(f"WARNING: プロセスチェックに失敗しました: {e}")
        return True

def check_disk_space():
    """ディスク容量をチェック"""
    try:
        import shutil
        
        total, used, free = shutil.disk_usage('.')
        free_mb = free / 1024 / 1024
        
        # 100MB以下の場合は警告
        if free_mb < 100:
            print(f"ERROR: ディスク容量が不足しています (残り: {free_mb:.1f}MB)")
            return False
        elif free_mb < 500:
            print(f"WARNING: ディスク容量が少なくなっています (残り: {free_mb:.1f}MB)")
        else:
            print(f"OK: ディスク容量は十分です (残り: {free_mb:.1f}MB)")
        
        return True
        
    except Exception as e:
        print(f"WARNING: ディスク容量チェックに失敗しました: {e}")
        return True

def main():
    """メインヘルスチェック関数"""
    print(f"=== ヘルスチェック開始: {datetime.now().isoformat()} ===")
    
    checks = [
        ("CSVファイル", check_csv_files),
        ("ログファイル", check_log_file), 
        ("プロセス健全性", check_process_health),
        ("ディスク容量", check_disk_space)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n--- {check_name}チェック ---")
        try:
            result = check_func()
            if not result:
                all_passed = False
                print(f"{check_name}: FAILED")
            else:
                print(f"{check_name}: PASSED")
        except Exception as e:
            print(f"{check_name}: ERROR - {e}")
            all_passed = False
    
    print(f"\n=== ヘルスチェック結果: {'HEALTHY' if all_passed else 'UNHEALTHY'} ===")
    
    # 終了コード設定
    if all_passed:
        sys.exit(0)  # 正常
    else:
        sys.exit(1)  # 異常

if __name__ == "__main__":
    main() 