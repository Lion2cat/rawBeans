def extract_weight(name, description=None):
    """从产品名称或描述中提取重量信息"""
    import re
    
    # 常见的重量单位模式
    weight_patterns = [
        r'(\d+(?:\.\d+)?)\s*[Ll][Bb][Ss]?', # 例如：1lb, 2lbs, 1.5 lbs
        r'(\d+(?:\.\d+)?)\s*[Oo][Zz]',      # 例如：12oz, 16 oz
        r'(\d+(?:\.\d+)?)\s*[Pp][Oo][Uu][Nn][Dd][Ss]?', # 例如：1pound, 2pounds
        r'(\d+(?:\.\d+)?)\s*[Kk][Gg]',      # 例如：1kg, 0.5kg
        r'(\d+(?:\.\d+)?)\s*[Gg][Rr][Aa][Mm][Ss]?', # 例如：500grams, 250gram
        r'(\d+(?:\.\d+)?)\s*[Bb][Aa][Gg]',  # 例如：60bag, 70kg bag
    ]
    
    # 在名称中查找
    if name:
        for pattern in weight_patterns:
            match = re.search(pattern, name)
            if match:
                value = float(match.group(1))
                unit = match.group(0)[len(match.group(1)):].strip()
                return {"value": value, "unit": unit}
    
    # 在描述中查找
    if description:
        for pattern in weight_patterns:
            match = re.search(pattern, description)
            if match:
                value = float(match.group(1))
                unit = match.group(0)[len(match.group(1)):].strip()
                return {"value": value, "unit": unit}
    
    # Genuine Origin通常使用70kg袋装
    return {"value": 70, "unit": "kg"} 