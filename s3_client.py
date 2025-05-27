#!/usr/bin/env python3
"""
AWS S3クライアント
Hyperliquid Data ScraperのCSVファイルをS3にアップロードする
"""

import os
import logging
import gzip
import shutil
from datetime import datetime, timezone
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import config

class S3Client:
    """
    AWS S3へのファイルアップロードを管理するクライアント
    """
    
    def __init__(self, bucket_name: str = None, region: str = None):
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME', config.S3_BUCKET_NAME)
        self.region = region or os.getenv('AWS_DEFAULT_REGION', config.S3_REGION)
        self.key_prefix = config.S3_KEY_PREFIX
        self.logger = logging.getLogger(__name__)
        
        # S3クライアントの初期化
        self.s3_client = None
        self._initialize_s3_client()
    
    def _initialize_s3_client(self):
        """S3クライアントを初期化"""
        try:
            # AWS認証情報の確認
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if not credentials:
                self.logger.warning("AWS認証情報が設定されていません。S3機能は無効化されます。")
                self.s3_client = None
                return
            
            # S3クライアントの作成
            self.s3_client = boto3.client('s3', region_name=self.region)
            
            # バケットの存在確認
            if self._check_bucket_exists():
                self.logger.info(f"S3クライアントを初期化しました: {self.bucket_name}")
            else:
                self.logger.warning(f"S3バケットが存在しないか、アクセスできません: {self.bucket_name}")
                self.s3_client = None
                
        except NoCredentialsError as e:
            self.logger.warning(f"AWS認証エラー: {e}")
            self.s3_client = None
        except Exception as e:
            self.logger.warning(f"S3クライアント初期化エラー: {e}")
            self.s3_client = None
    
    def _check_bucket_exists(self) -> bool:
        """S3バケットの存在確認"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.logger.error(f"S3バケットが存在しません: {self.bucket_name}")
            elif error_code == '403':
                self.logger.error(f"S3バケットへのアクセス権限がありません: {self.bucket_name}")
            else:
                self.logger.error(f"S3バケットチェックエラー: {e}")
            return False
        except Exception as e:
            self.logger.error(f"S3バケットチェック中の予期しないエラー: {e}")
            return False
    
    def upload_file(self, local_file_path: str, s3_key: str = None, compress: bool = None) -> bool:
        """
        ローカルファイルをS3にアップロード
        
        Args:
            local_file_path: ローカルファイルパス
            s3_key: S3オブジェクトキー（Noneの場合はファイル名から自動生成）
            compress: ファイルを圧縮するかどうか（Noneの場合は設定値を使用）
            
        Returns:
            bool: アップロード成功の場合True
        """
        if not self.s3_client:
            self.logger.error("S3クライアントが初期化されていません")
            return False
        
        if not os.path.exists(local_file_path):
            self.logger.error(f"ローカルファイルが存在しません: {local_file_path}")
            return False
        
        try:
            # S3キーの生成
            if not s3_key:
                filename = os.path.basename(local_file_path)
                timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
                s3_key = f"{self.key_prefix}{timestamp}/{filename}"
            
            # 圧縮設定
            should_compress = compress if compress is not None else config.S3_COMPRESS_FILES
            
            # ファイルのアップロード処理
            if should_compress and not local_file_path.endswith('.gz'):
                return self._upload_compressed_file(local_file_path, s3_key)
            else:
                return self._upload_regular_file(local_file_path, s3_key)
                
        except Exception as e:
            self.logger.error(f"ファイルアップロードエラー {local_file_path}: {e}")
            return False
    
    def _upload_regular_file(self, local_file_path: str, s3_key: str) -> bool:
        """通常のファイルアップロード"""
        try:
            # メタデータの設定
            metadata = {
                'upload-timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'hyperliquid-data-scraper',
                'file-type': 'csv-data'
            }
            
            # ファイルアップロード
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'Metadata': metadata,
                    'ContentType': 'text/csv'
                }
            )
            
            file_size = os.path.getsize(local_file_path)
            self.logger.info(f"S3アップロード完了: {s3_key} ({file_size:,}バイト)")
            return True
            
        except Exception as e:
            self.logger.error(f"通常ファイルアップロードエラー {local_file_path}: {e}")
            return False
    
    def _upload_compressed_file(self, local_file_path: str, s3_key: str) -> bool:
        """圧縮ファイルアップロード"""
        compressed_file_path = None
        try:
            # 一時的な圧縮ファイルを作成
            compressed_file_path = f"{local_file_path}.gz"
            
            with open(local_file_path, 'rb') as f_in:
                with gzip.open(compressed_file_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # メタデータの設定
            metadata = {
                'upload-timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'hyperliquid-data-scraper',
                'file-type': 'csv-data',
                'compression': 'gzip'
            }
            
            # 圧縮ファイルをアップロード
            compressed_s3_key = f"{s3_key}.gz"
            self.s3_client.upload_file(
                compressed_file_path,
                self.bucket_name,
                compressed_s3_key,
                ExtraArgs={
                    'Metadata': metadata,
                    'ContentType': 'application/gzip',
                    'ContentEncoding': 'gzip'
                }
            )
            
            original_size = os.path.getsize(local_file_path)
            compressed_size = os.path.getsize(compressed_file_path)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            self.logger.info(
                f"S3圧縮アップロード完了: {compressed_s3_key} "
                f"({original_size:,} → {compressed_size:,}バイト, "
                f"圧縮率: {compression_ratio:.1f}%)"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"圧縮ファイルアップロードエラー {local_file_path}: {e}")
            return False
        finally:
            # 一時的な圧縮ファイルを削除
            if compressed_file_path and os.path.exists(compressed_file_path):
                os.remove(compressed_file_path)
    
    def upload_multiple_files(self, file_paths: List[str]) -> Dict[str, bool]:
        """
        複数ファイルの一括アップロード
        
        Args:
            file_paths: アップロードするファイルパスのリスト
            
        Returns:
            Dict[str, bool]: ファイルパスとアップロード結果の辞書
        """
        results = {}
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                results[file_path] = self.upload_file(file_path)
            else:
                self.logger.warning(f"ファイルが存在しません: {file_path}")
                results[file_path] = False
        
        success_count = sum(1 for success in results.values() if success)
        self.logger.info(f"一括アップロード完了: {success_count}/{len(file_paths)}ファイル成功")
        
        return results
    
    def list_bucket_objects(self, prefix: str = None) -> List[Dict]:
        """
        S3バケット内のオブジェクト一覧を取得
        
        Args:
            prefix: オブジェクトキーのプレフィックス
            
        Returns:
            List[Dict]: オブジェクト情報のリスト
        """
        if not self.s3_client:
            self.logger.error("S3クライアントが初期化されていません")
            return []
        
        try:
            list_prefix = prefix or self.key_prefix
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=list_prefix
            )
            
            objects = response.get('Contents', [])
            self.logger.info(f"S3オブジェクト一覧取得: {len(objects)}個のオブジェクト")
            
            return objects
            
        except Exception as e:
            self.logger.error(f"S3オブジェクト一覧取得エラー: {e}")
            return []
    
    def delete_old_files(self, days_to_keep: int = 30) -> int:
        """
        古いファイルを削除
        
        Args:
            days_to_keep: 保持する日数
            
        Returns:
            int: 削除されたファイル数
        """
        if not self.s3_client:
            self.logger.error("S3クライアントが初期化されていません")
            return 0
        
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            objects = self.list_bucket_objects()
            
            objects_to_delete = []
            for obj in objects:
                if obj['LastModified'] < cutoff_date:
                    objects_to_delete.append({'Key': obj['Key']})
            
            if not objects_to_delete:
                self.logger.info("削除対象のファイルはありません")
                return 0
            
            # バッチ削除
            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            
            deleted_count = len(response.get('Deleted', []))
            self.logger.info(f"古いファイルを削除しました: {deleted_count}個")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"古いファイル削除エラー: {e}")
            return 0
    
    def is_available(self) -> bool:
        """S3クライアントが利用可能かどうか"""
        return self.s3_client is not None
    
    def get_upload_statistics(self) -> Dict:
        """アップロード統計情報を取得"""
        if not self.s3_client:
            return {"available": False, "error": "S3クライアントが初期化されていません"}
        
        try:
            objects = self.list_bucket_objects()
            
            total_size = sum(obj.get('Size', 0) for obj in objects)
            total_files = len(objects)
            
            # 最新ファイルの情報
            latest_file = None
            if objects:
                latest_file = max(objects, key=lambda x: x['LastModified'])
            
            return {
                "available": True,
                "bucket_name": self.bucket_name,
                "total_files": total_files,
                "total_size_bytes": total_size,
                "latest_file": {
                    "key": latest_file['Key'] if latest_file else None,
                    "last_modified": latest_file['LastModified'].isoformat() if latest_file else None,
                    "size": latest_file.get('Size', 0) if latest_file else 0
                } if latest_file else None
            }
            
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            } 