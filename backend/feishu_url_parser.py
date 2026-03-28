"""
飞书链接解析工具
支持自动解析飞书多维表格链接，提取Base ID和Table ID
"""

import re
import urllib.parse

def parse_feishu_url(url):
    """
    解析飞书多维表格链接
    
    Args:
        url (str): 飞书链接，如 https://example.feishu.cn/base/bascnxxxxxxx?table=tblxxxxxxxxx
                           或 https://xxx.feishu.cn/wiki/xxxxx?table=xxxxx&view=xxxxx
    
    Returns:
        dict: 包含base_id, table_id, view_id的字典
    """
    if not url:
        return {"error": "链接不能为空"}
    
    try:
        # 解析URL
        parsed = urllib.parse.urlparse(url)
        
        # 提取base_id, table_id, view_id
        base_id = None
        table_id = None
        view_id = None
        
        # 从查询参数中提取（优先级最高）
        query_params = urllib.parse.parse_qs(parsed.query)
        
        if 'table' in query_params:
            table_id = query_params['table'][0]
        
        if 'view' in query_params:
            view_id = query_params['view'][0]
        
        # 从路径中提取
        path_parts = parsed.path.strip('/').split('/')
        
        # 处理 /base/xxxxx 格式
        for i, part in enumerate(path_parts):
            if part == 'base' and i + 1 < len(path_parts):
                base_id = path_parts[i + 1]
            elif part == 'table' and i + 1 < len(path_parts):
                table_id = path_parts[i + 1]
            elif part == 'view' and i + 1 < len(path_parts):
                view_id = path_parts[i + 1]
        
        # 处理 /wiki/xxxxx 格式（飞书多维表格的wiki链接）
        # 这种情况下，base_id通常在wiki后面的部分，或者需要特殊处理
        if 'wiki' in path_parts and not base_id:
            # 对于wiki链接，可能需要从其他地方获取base_id
            # 这里我们先尝试从路径中提取
            wiki_index = path_parts.index('wiki')
            if wiki_index + 1 < len(path_parts):
                potential_base = path_parts[wiki_index + 1]
                # 检查是否看起来像base_id格式
                if potential_base.startswith('basc') or len(potential_base) > 10:
                    base_id = potential_base
        
        # 验证提取的ID
        if not table_id:
            return {"error": "无法从链接中提取Table ID"}
        
        result = {
            "table_id": table_id,
            "view_id": view_id,
            "success": True
        }
        
        # Base ID可能是可选的（某些飞书链接格式中不包含）
        if base_id:
            result["base_id"] = base_id
        
        return result
        
    except Exception as e:
        return {"error": f"链接解析失败: {str(e)}"}

def extract_feishu_ids_from_text(text):
    """
    从文本中提取飞书链接并解析
    
    Args:
        text (str): 包含飞书链接的文本
    
    Returns:
        list: 解析结果列表
    """
    if not text:
        return []
    
    # 飞书链接的正则表达式
    feishu_url_pattern = r'https?://[^\s]+\.feishu\.cn/[^\s]+'
    
    # 查找所有飞书链接
    urls = re.findall(feishu_url_pattern, text)
    
    results = []
    for url in urls:
        parsed = parse_feishu_url(url)
        if parsed.get('success'):
            results.append({
                "url": url,
                "parsed": parsed
            })
    
    return results

def format_feishu_url(base_id, table_id, view_id=None):
    """
    格式化飞书链接
    
    Args:
        base_id (str): Base ID
        table_id (str): Table ID  
        view_id (str, optional): View ID
    
    Returns:
        str: 格式化的飞书链接
    """
    url = f"https://example.feishu.cn/base/{base_id}"
    if table_id:
        url += f"?table={table_id}"
    if view_id:
        separator = "&" if table_id else "?"
        url += f"{separator}view={view_id}"
    
    return url

# 测试用例
if __name__ == "__main__":
    # 测试链接解析
    test_urls = [
        "https://example.feishu.cn/base/bascnxxxxxxx?table=tblxxxxxxxxx",
        "https://example.feishu.cn/base/bascnxxxxxxx/table/tblxxxxxxxxx/view/vewxxxxxxxxx",
        "https://example.feishu.cn/base/bascnxxxxxxx?table=tblxxxxxxxxx&view=vewxxxxxxxxx",
    ]
    
    print("=== 飞书链接解析测试 ===")
    for url in test_urls:
        result = parse_feishu_url(url)
        print(f"URL: {url}")
        print(f"解析结果: {result}")
        print("-" * 50)
    
    # 测试文本提取
    test_text = """
    请查看这个飞书表格：https://example.feishu.cn/base/bascnxxxxxxx?table=tblxxxxxxxxx
    还有这个：https://example.feishu.cn/base/bascnxxxxxxx/table/tblxxxxxxxxx
    """
    
    print("=== 文本中链接提取测试 ===")
    extracted = extract_feishu_ids_from_text(test_text)
    for item in extracted:
        print(f"链接: {item['url']}")
        print(f"解析: {item['parsed']}")
        print("-" * 50)
