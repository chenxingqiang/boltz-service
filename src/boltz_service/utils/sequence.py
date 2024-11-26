import re
from typing import Optional

def validate_sequence(sequence: str) -> bool:
    """验证蛋白质序列是否有效
    
    Parameters
    ----------
    sequence : str
        输入序列
        
    Returns
    -------
    bool
        序列是否有效
        
    """
    if not sequence:
        return False
        
    # 检查序列长度
    if len(sequence) > 2000:
        return False
        
    # 检查氨基酸字符
    valid_chars = set("ACDEFGHIKLMNPQRSTVWY")
    sequence_chars = set(sequence.upper())
    
    return sequence_chars.issubset(valid_chars)

def format_sequence(sequence: str) -> Optional[str]:
    """格式化蛋白质序列
    
    Parameters
    ----------
    sequence : str
        输入序列
        
    Returns
    -------
    str or None
        格式化后的序列，如果序列无效则返回None
        
    """
    # 移除空白字符
    sequence = re.sub(r"\s+", "", sequence)
    
    # 转换为大写
    sequence = sequence.upper()
    
    # 验证序列
    if not validate_sequence(sequence):
        return None
        
    return sequence
