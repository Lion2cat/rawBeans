import json
import os
from datetime import datetime
from pathlib import Path

class RawBeansPipeline:
    """
    处理爬取的咖啡生豆数据，将其保存到JSON文件
    """
    
    def __init__(self):
        # 确保结果目录存在
        self.results_dir = Path('results')
        self.results_dir.mkdir(exist_ok=True)
        self.items = []
        
    def process_item(self, item, spider):
        # 添加时间戳
        if 'updated_at' not in item:
            item['updated_at'] = datetime.now().strftime('%Y-%m-%d')
            
        # 标准化价格
        if 'price' in item and item['price']:
            # 移除价格中的货币符号和空格
            if isinstance(item['price'], str):
                item['price'] = item['price'].replace('$', '').replace(' ', '').strip()
                try:
                    item['price'] = float(item['price'])
                except ValueError:
                    spider.logger.warning(f"无法转换价格: {item['price']}")
        
        # 保存项目
        self.items.append(dict(item))
        spider.logger.info(f"处理项目: {item.get('name', 'unknown')}")
        return item
    
    def close_spider(self, spider):
        """爬虫关闭时保存所有项目到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.results_dir / f"{spider.name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)
            
        spider.logger.info(f"已保存 {len(self.items)} 项到 {filename}") 