from scrapy import Item, Field

class BeanItem(Item):
    """
    咖啡生豆价格数据项
    存储从供应商网站抓取的基本信息
    """
    # 基本信息
    name = Field()          # 咖啡豆名称
    origin = Field()        # 产地
    supplier = Field()      # 供应商
    
    # 价格信息
    price = Field()         # 价格
    currency = Field()      # 货币 (默认USD)
    weight = Field()        # 重量和单位，如"1 lb"
    
    # 元数据
    url = Field()           # 数据来源URL
    updated_at = Field()    # 价格更新日期
    
    # 可选信息
    description = Field()   # 产品描述
    process = Field()       # 处理方法
    variety = Field()       # 品种
    score = Field()         # 评分（如果有） 