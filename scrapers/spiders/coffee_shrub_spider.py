import scrapy
import re
from datetime import datetime
from scrapers.items import BeanItem

class CoffeeShrubSpider(scrapy.Spider):
    """
    抓取Coffee Shrub网站的生豆数据
    """
    name = "coffee_shrub"
    allowed_domains = ["coffeeshrub.com"]
    start_urls = [
        "https://www.coffeeshrub.com/green-coffee.html?product_list_limit=all&sm_status=1"
    ]
    
    def parse(self, response):
        """解析产品列表页面"""
        self.logger.info(f"正在解析: {response.url}")
        
        # 查找所有产品项
        products = response.css('.products .product-item')
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
                item['supplier'] = 'Coffee Shrub'
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
            # 提取重量信息
            weight_options = response.css('.swatch-attribute.weight .swatch-option::text').getall()
            if weight_options:
                item['weight'] = ' | '.join([w.strip() for w in weight_options if w.strip()])
            
            # 提取详细描述
            description = response.css('.product.attribute.description .value ::text').getall()
            if description:
                item['description'] = ' '.join([d.strip() for d in description if d.strip()])
            
            # 提取产地（如果之前未能提取）
            if 'origin' not in item or not item['origin']:
                # 从描述或产品标题中尝试提取
                if 'description' in item and item['description']:
                    origin = self.extract_origin_from_description(item['description'])
                    if origin:
                        item['origin'] = origin
                        
            # 提取规格表中的信息
            specs_rows = response.css('.additional-attributes-wrapper tbody tr')
            for row in specs_rows:
                label = row.css('th::text').get()
                value = row.css('td::text').get()
                
                if label and value:
                    label = label.strip().lower()
                    value = value.strip()
                    
                    if "origin" in label or "country" in label:
                        item['origin'] = value
                    elif "process" in label or "preparation" in label:
                        item['process'] = value
                    elif "variety" in label:
                        item['variety'] = value
            
            # 如果描述中存在处理方法和品种信息，但之前没有提取到
            if 'description' in item and item['description']:
                if 'process' not in item or not item['process']:
                    process = self.extract_process(item['description'])
                    if process:
                        item['process'] = process
                
                if 'variety' not in item or not item['variety']:
                    variety = self.extract_variety(item['description'])
                    if variety:
                        item['variety'] = variety
            
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
            r'from\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',
            r'grown in\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)',
            r'([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+coffee'
        ]
        
        for pattern in origin_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                potential_origin = match.group(1).strip()
                # 过滤掉一些常见的误匹配
                if potential_origin.lower() not in ['this', 'these', 'those', 'our', 'their']:
                    return potential_origin
        
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