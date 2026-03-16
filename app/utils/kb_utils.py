import re
import hashlib


def safe_collection_name(raw_name: str) -> str:
    """
    将任意字符串转换为合法的 ChromaDB 集合名。
    规则：长度3-512，只能包含 [a-zA-Z0-9._-]，首尾必须是字母或数字。
    """
    # 如果已经是合法名称，直接返回
    if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]$', raw_name):
        return raw_name

    # 否则，生成基于哈希的合法名称
    hash_hex = hashlib.md5(raw_name.encode('utf-8')).hexdigest()[:16]  # 16位十六进制
    safe_name = f"kb_{hash_hex}"
    return safe_name