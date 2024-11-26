#!/usr/bin/env python3
"""数据库下载脚本"""

import argparse
import logging
import os
import sys

from boltz_service.utils.db_manager import DatabaseManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="下载和管理数据库")
    parser.add_argument(
        "--target-dir",
        default="~/.boltz/db",
        help="数据库目标目录"
    )
    parser.add_argument(
        "--database",
        choices=["bfd", "uniref", "all"],
        default="all",
        help="要下载的数据库"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="检查数据库健康状态"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="显示数据库信息"
    )
    parser.add_argument(
        "--cleanup-cache",
        action="store_true",
        help="清理缓存"
    )
    parser.add_argument(
        "--max-cache-size",
        type=int,
        default=100 * 1024 * 1024 * 1024,
        help="最大缓存大小(字节)"
    )
    
    args = parser.parse_args()
    
    # 创建数据库管理器
    manager = DatabaseManager()
    
    # 检查健康状态
    if args.check:
        logger.info("检查数据库健康状态...")
        errors = manager.check_database_health()
        if errors:
            logger.error("发现以下问题:")
            for error in errors:
                logger.error(f"- {error}")
            sys.exit(1)
        else:
            logger.info("数据库状态正常")
            
    # 显示信息
    if args.info:
        logger.info("数据库信息:")
        info = manager.get_database_info()
        for db_name, status in info["status"].items():
            logger.info(f"\n{db_name}:")
            for key, value in status.items():
                logger.info(f"  {key}: {value}")
                
    # 下载数据库
    if args.database in ["bfd", "all"]:
        logger.info("下载BFD数据库...")
        try:
            manager.download_bfd(args.target_dir)
            logger.info("BFD数据库下载完成")
        except Exception as e:
            logger.error(f"下载BFD数据库失败: {e}")
            sys.exit(1)
            
    # 清理缓存
    if args.cleanup_cache:
        logger.info("清理缓存...")
        cache_dir = os.path.expanduser("~/.boltz/cache")
        manager.cleanup_cache(cache_dir, args.max_cache_size)
        logger.info("缓存清理完成")

if __name__ == "__main__":
    main()
