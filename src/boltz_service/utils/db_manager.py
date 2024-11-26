"""数据库管理工具"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

import requests
from tqdm import tqdm

from boltz_service.utils.database_config import BFDConfig, DatabaseConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, base_dir: str = "~/.boltz"):
        self.base_dir = os.path.expanduser(base_dir)
        self.db_dir = os.path.join(self.base_dir, "db")
        self.version_file = os.path.join(self.base_dir, "db_versions.json")
        self._setup_dirs()
        
    def _setup_dirs(self):
        """创建必要的目录"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.db_dir, exist_ok=True)
        
    def _load_versions(self) -> Dict[str, str]:
        """加载数据库版本信息
        
        Returns
        -------
        dict[str, str]
            数据库版本信息
            
        """
        if not os.path.exists(self.version_file):
            return {}
            
        with open(self.version_file) as f:
            return json.load(f)
            
    def _save_versions(self, versions: Dict[str, str]):
        """保存数据库版本信息
        
        Parameters
        ----------
        versions : dict[str, str]
            数据库版本信息
            
        """
        with open(self.version_file, "w") as f:
            json.dump(versions, f, indent=2)
            
    def _calculate_md5(self, file_path: str) -> str:
        """计算文件MD5
        
        Parameters
        ----------
        file_path : str
            文件路径
            
        Returns
        -------
        str
            MD5哈希值
            
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    def download_bfd(self, target_dir: str):
        """下载BFD数据库
        
        Parameters
        ----------
        target_dir : str
            目标目录
            
        """
        target_dir = os.path.expanduser(target_dir)
        os.makedirs(target_dir, exist_ok=True)
        
        # 下载文件
        url = "https://bfd.mmseqs.com/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz"
        output = os.path.join(target_dir, "bfd.tar.gz")
        
        logger.info(f"Downloading BFD database to {output}")
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get("content-length", 0))
        
        with open(output, "wb") as f, tqdm(
            total=total_size,
            unit="iB",
            unit_scale=True
        ) as pbar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                pbar.update(size)
                
        # 解压文件
        logger.info("Extracting files...")
        subprocess.run(
            ["tar", "xzf", output],
            cwd=target_dir,
            check=True
        )
        
        # 删除压缩包
        os.remove(output)
        
        # 验证文件
        logger.info("Verifying files...")
        config = BFDConfig.from_env()
        if not config:
            raise RuntimeError("Failed to verify BFD database")
            
        # 更新版本信息
        versions = self._load_versions()
        versions["bfd"] = "1.0.0"
        self._save_versions(versions)
        
    def check_database_health(self) -> List[str]:
        """检查数据库健康状态
        
        Returns
        -------
        list[str]
            错误信息列表
            
        """
        errors = []
        config = DatabaseConfig.from_env()
        
        # 检查BFD
        if config.bfd:
            for name, path in asdict(config.bfd).items():
                if not os.path.exists(path):
                    errors.append(f"BFD {name} not found: {path}")
                    
        # 检查UniRef
        if config.uniref_path and not os.path.exists(config.uniref_path):
            errors.append(f"UniRef database not found: {config.uniref_path}")
            
        # 检查分类数据库
        if config.taxonomy_path and not os.path.exists(config.taxonomy_path):
            errors.append(f"Taxonomy database not found: {config.taxonomy_path}")
            
        return errors
        
    def cleanup_cache(self, cache_dir: str, max_size: int = 100 * 1024 * 1024 * 1024):
        """清理缓存目录
        
        Parameters
        ----------
        cache_dir : str
            缓存目录
        max_size : int
            最大缓存大小(字节)
            
        """
        cache_dir = os.path.expanduser(cache_dir)
        if not os.path.exists(cache_dir):
            return
            
        # 获取所有缓存文件
        files = []
        total_size = 0
        for path in Path(cache_dir).rglob("*"):
            if path.is_file():
                size = path.stat().st_size
                mtime = path.stat().st_mtime
                files.append((path, size, mtime))
                total_size += size
                
        # 如果超过最大大小,删除最旧的文件
        if total_size > max_size:
            logger.info(f"Cache size ({total_size} bytes) exceeds limit ({max_size} bytes)")
            files.sort(key=lambda x: x[2])  # 按修改时间排序
            
            for path, size, _ in files:
                if total_size <= max_size:
                    break
                    
                try:
                    path.unlink()
                    total_size -= size
                    logger.info(f"Removed cache file: {path}")
                except OSError as e:
                    logger.warning(f"Failed to remove cache file {path}: {e}")
                    
    def get_database_info(self) -> Dict[str, dict]:
        """获取数据库信息
        
        Returns
        -------
        dict[str, dict]
            数据库信息
            
        """
        versions = self._load_versions()
        config = DatabaseConfig.from_env()
        
        info = {
            "versions": versions,
            "status": {}
        }
        
        # BFD状态
        if config.bfd:
            info["status"]["bfd"] = {
                "available": True,
                "path": str(config.bfd.db_path),
                "size": sum(
                    os.path.getsize(p) for p in asdict(config.bfd).values()
                    if os.path.exists(p)
                )
            }
        else:
            info["status"]["bfd"] = {"available": False}
            
        # UniRef状态
        if config.uniref_path:
            info["status"]["uniref"] = {
                "available": True,
                "path": str(config.uniref_path),
                "size": os.path.getsize(config.uniref_path)
            }
        else:
            info["status"]["uniref"] = {"available": False}
            
        # 分类数据库状态
        if config.taxonomy_path:
            info["status"]["taxonomy"] = {
                "available": True,
                "path": str(config.taxonomy_path),
                "size": os.path.getsize(config.taxonomy_path)
            }
        else:
            info["status"]["taxonomy"] = {"available": False}
            
        return info
