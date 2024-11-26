"""数据库配置"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class BFDConfig:
    """BFD数据库配置"""
    
    # 数据库路径
    db_path: Path
    # ffindex文件
    ffindex: Path
    # ffdata文件 
    ffdata: Path
    # cs219索引
    cs219_index: Path
    # cs219数据
    cs219_data: Path
    # hhm索引
    hhm_index: Path
    # hhm数据
    hhm_data: Path
    
    @classmethod
    def from_env(cls) -> Optional['BFDConfig']:
        """从环境变量创建配置
        
        Returns
        -------
        BFDConfig or None
            BFD配置,如果环境变量未设置则返回None
            
        """
        db_path = os.getenv("BOLTZ_BFD_PATH")
        if not db_path:
            return None
            
        db_path = Path(db_path)
        if not db_path.exists():
            return None
            
        # 检查所需文件
        base = "bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt"
        required_files = {
            "ffindex": f"{base}_a3m.ffindex",
            "ffdata": f"{base}_a3m.ffdata",
            "cs219_index": f"{base}_cs219.ffindex", 
            "cs219_data": f"{base}_cs219.ffdata",
            "hhm_index": f"{base}_hhm.ffindex",
            "hhm_data": f"{base}_hhm.ffdata"
        }
        
        # 验证文件MD5
        expected_md5 = {
            "ffindex": "476941cf4a964d96fb3b68a82fe734d1",
            "ffdata": "2dc0f09adabbcf1965ed578e0b2ab07e",
            "cs219_index": "26d48869efdb50d036e2fb9056a0ae9d",
            "cs219_data": "4bb63ac9c3a3dd088cf654df1f548d53", 
            "hhm_index": "799f308b20627088129847709f1abed6",
            "hhm_data": "9bd2da8a8adbcc30801f0221d0dc1987"
        }
        
        files = {}
        for key, filename in required_files.items():
            path = db_path / filename
            if not path.exists():
                return None
            files[key] = path
            
        return cls(
            db_path=db_path,
            **files
        )

@dataclass
class DatabaseConfig:
    """数据库配置"""
    
    # BFD配置
    bfd: Optional[BFDConfig] = None
    # UniRef配置
    uniref_path: Optional[Path] = None
    # 分类数据库配置  
    taxonomy_path: Optional[Path] = None
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """从环境变量创建配置
        
        Returns
        -------
        DatabaseConfig
            数据库配置
            
        """
        bfd = BFDConfig.from_env()
        uniref = os.getenv("BOLTZ_UNIREF_PATH")
        taxonomy = os.getenv("BOLTZ_TAXONOMY_PATH")
        
        return cls(
            bfd=bfd,
            uniref_path=Path(uniref) if uniref else None,
            taxonomy_path=Path(taxonomy) if taxonomy else None
        )
