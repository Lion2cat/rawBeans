import scrapy
import re
from datetime import datetime
from scrapers.items import BeanItem

class SweetMariasSpider(scrapy.Spider):
    """
    抓取Sweet Maria's网站的生豆数据
    """
    name = "sweet_marias"
    allowed_domains = ["sweetmarias.com"]
    start_urls = [
        "https://www.sweetmarias.com/green-coffee.html?product_list_limit=all&sm_status=1"
    ]
    
    def parse(self, response):
        """解析产品列表页面"""
        self.logger.info(f"正在解析: {response.url}")
        
        # 查找所有产品项
        products = response.css('li.product-item')
        self.logger.info(f"找到 {len(products)} 个产品")
        
        # 遍历产品列表
        for product in products:
            try:
                # 提取基本信息
                name = product.css('.product-item-link::text').get()
                if name:
                    name = name.strip()
                
                # 提取价格信息
                price_elem = product.css('.price-container .price::text').get()
                price = None
                if price_elem:
                    price = price_elem.strip()
                    # 去除$符号
                    price = price.replace('$', '')
                
                # 提取产品URL
                url = product.css('.product-item-link::attr(href)').get()
                
                # 创建临时项目
                item = BeanItem()
                item['name'] = name
                item['price'] = price
                item['currency'] = 'USD'
                item['supplier'] = 'Sweet Marias'
                item['url'] = url
                item['updated_at'] = datetime.now().strftime('%Y-%m-%d')
                
                # 尝试从名称中提取产地
                origin = self.extract_origin(name)
                if origin:
                    item['origin'] = origin
                
                # 获取产品详情页
                if url:
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_detail,
                        meta={'item': item}
                    )
                else:
                    # 如果没有URL，直接返回基本信息
                    yield item
                    
            except Exception as e:
                self.logger.error(f"解析产品时出错: {e}")
    
    def parse_detail(self, response):
        """解析产品详情页"""
        item = response.meta['item']
        self.logger.info(f"正在解析产品详情: {response.url}")
        
        # 提取详细信息
        try:
            # 提取详细描述
            description = response.css('.product.attribute.description .value ::text').getall()
            if description:
                item['description'] = ' '.join([d.strip() for d in description if d.strip()])
            
            # 提取重量信息
            weight_options = response.css('.swatch-attribute.weight .swatch-option::text').getall()
            if weight_options:
                item['weight'] = ' | '.join([w.strip() for w in weight_options if w.strip()])
            
            # 尝试提取产地（如果之前未能提取）
            if 'origin' not in item or not item['origin']:
                # 从描述中尝试提取
                if 'description' in item and item['description']:
                    origin = self.extract_origin_from_description(item['description'])
                    if origin:
                        item['origin'] = origin
            
            # 尝试提取处理方法
            if 'description' in item and item['description']:
                process = self.extract_process(item['description'])
                if process:
                    item['process'] = process
            
            # 尝试提取品种
            if 'description' in item and item['description']:
                variety = self.extract_variety(item['description'])
                if variety:
                    item['variety'] = variety
            
            # 尝试提取评分
            score_text = response.css('.sm_specs tbody tr:contains("Score") td:last-child::text').get()
            if score_text:
                score_match = re.search(r'(\d+\.?\d*)', score_text)
                if score_match:
                    item['score'] = score_match.group(1)
        
        except Exception as e:
            self.logger.error(f"解析详情页时出错: {e}")
        
        # 返回完整项目
        yield item
    
    def extract_origin(self, name):
        """尝试从名称中提取产地"""
        # 常见产地列表
        origins = [
            'Ethiopia', 'Kenya', 'Colombia', 'Guatemala', 'Costa Rica', 'El Salvador',
            'Honduras', 'Nicaragua', 'Panama', 'Mexico', 'Brazil', 'Peru', 'Burundi',
            'Rwanda', 'Tanzania', 'Uganda', 'Yemen', 'Indonesia', 'Papua New Guinea',
            'East Timor', 'India', 'Sumatra', 'Java', 'Sulawesi'
        ]
        
        # 查找产地
        for origin in origins:
            if origin in name:
                return origin
        
        return None
    
    def extract_origin_from_description(self, description):
        """从描述中提取产地"""
        # 尝试找出常见产地模式
        origin_patterns = [
            r'from\s+([A-Za-z]+(?:\s+[A-Za-z]+)?),',
            r'grown in\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',
            r'([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+coffee'
        ]
        
        for pattern in origin_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_process(self, description):
        """从描述中提取处理方法"""
        # 常见处理方法
        processes = [
            'Washed', 'Natural', 'Honey', 'Pulped Natural', 'Wet Hulled',
            'Dry Process', 'Wet Process'
        ]
        
        # 查找处理方法
        for process in processes:
            if process in description:
                return process
        
        return None
    
    def extract_variety(self, description):
        """从描述中提取品种"""
        # 常见品种
        varieties = [
            'Bourbon', 'Typica', 'Caturra', 'Catuai', 'Gesha', 'Geisha',
            'SL28', 'SL34', 'Pacas', 'Pacamara', 'Maragogipe', 'Mundo Novo',
            'Ethiopian Heirloom', 'Heirloom', 'Java'
        ]
        
        # 查找品种
        for variety in varieties:
            if variety in description:
                return variety
        
        return None 