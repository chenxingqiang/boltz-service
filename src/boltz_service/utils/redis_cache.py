"""Redis缓存工具"""

import os
from typing import Optional

import redis

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
        
    def get_stats(self) -> dict:
        """获取缓存统计信息
        
        Returns
        -------
        dict
            缓存统计信息
            
        """
        info = self.client.info()
        return {
            "used_memory": info["used_memory"],
            "used_memory_peak": info["used_memory_peak"],
            "total_keys": self.client.dbsize(),
            "hit_rate": info.get("keyspace_hits", 0) / (
                info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1)
            ) * 100
        }
        
    def cleanup(self, pattern: str = "msa:*"):
        """清理缓存
        
        Parameters
        ----------
        pattern : str
            要清理的键模式
            
        """
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern)
            if keys:
                self.client.delete(*keys)
            if cursor == 0:
                break

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
    
    try:
        cache = RedisCache(host=host, port=port, db=db, password=password)
        # 测试连接
        cache.client.ping()
        return cache
    except redis.ConnectionError:
        return None
