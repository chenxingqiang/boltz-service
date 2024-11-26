import os
from pathlib import Path
from typing import Optional, Dict

import redis
import sqlite3

class TaxonomyDB:
    """分类数据库接口"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        
    def connect(self):
        """连接到数据库"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            
    def close(self):
        """关闭数据库连接"""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            
    def get(self, uniref_id: str) -> Optional[str]:
        """获取分类ID
        
        Parameters
        ----------
        uniref_id : str
            UniRef ID
            
        Returns
        -------
        str or None
            分类ID，如果不存在则返回None
            
        """
        if self._conn is None:
            self.connect()
            
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT taxonomy_id FROM taxonomy WHERE uniref_id = ?",
            (uniref_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

class RedisCache:
    """Redis缓存接口"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None
    ):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
    def get_msa(self, sequence: str) -> Optional[str]:
        """从缓存获取MSA
        
        Parameters
        ----------
        sequence : str
            蛋白质序列
            
        Returns
        -------
        str or None
            MSA文件路径，如果不存在则返回None
            
        """
        return self.client.get(f"msa:{sequence}")
        
    def set_msa(self, sequence: str, msa_path: str, expire: int = 86400):
        """将MSA添加到缓存
        
        Parameters
        ----------
        sequence : str
            蛋白质序列
        msa_path : str
            MSA文件路径
        expire : int
            过期时间（秒）
            
        """
        self.client.set(f"msa:{sequence}", msa_path, ex=expire)

def get_taxonomy_db() -> Dict[str, str]:
    """获取分类数据库
    
    Returns
    -------
    dict[str, str]
        分类数据库
        
    """
    db_path = os.getenv("BOLTZ_TAXONOMY_DB")
    if not db_path:
        return {}
        
    db = TaxonomyDB(db_path)
    return db

def get_redis_cache() -> Optional[RedisCache]:
    """获取Redis缓存
    
    Returns
    -------
    RedisCache or None
        Redis缓存实例，如果配置不存在则返回None
        
    """
    host = os.getenv("REDIS_HOST")
    if not host:
        return None
        
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD")
    
    return RedisCache(host=host, port=port, db=db, password=password)
