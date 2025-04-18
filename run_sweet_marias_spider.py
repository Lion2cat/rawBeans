import os
import sys
import json
import logging
import time
import random
from pathlib import Path
from datetime import datetime
import re

# 导入undetected-chromedriver来绕过Cloudflare
import undetected_chromedriver as uc

# Selenium相关导入
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# BeautifulSoup用于解析页面
from bs4 import BeautifulSoup

# 添加导入爬虫类（只用于获取常量）
from scrapers.spiders.sweet_marias_spider import SweetMariasSpider

def setup_driver():
    """配置undetected-chromedriver，绕过Cloudflare防护"""
    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # 设置更真实的用户代理
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 初始化undetected-chromedriver
    driver = uc.Chrome(options=options)
    
    # 设置页面加载超时
    driver.set_page_load_timeout(60)
    
    return driver

def wait_for_cloudflare(driver, timeout=30):
    """等待Cloudflare验证完成"""
    logger = logging.getLogger(__name__)
    logger.info("等待Cloudflare验证...")
    
    try:
        # 检查是否存在Cloudflare挑战页面元素
        cloudflare_selectors = [
            "div.cf-browser-verification", 
            "#cf-please-wait",
            "iframe[src*='challenges.cloudflare.com']",
            ".cf-error-code"
        ]
        
        # 如果存在任何Cloudflare元素，等待它们消失
        for selector in cloudflare_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logger.info(f"检测到Cloudflare挑战: {selector}")
                # 等待所有Cloudflare元素消失
                wait = WebDriverWait(driver, timeout)
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, selector)))
                logger.info("Cloudflare验证完成")
                # 额外等待页面内容加载
                time.sleep(5)
                return True
        
        # 确认页面上有实际内容，不是挑战页面
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        
        # 简单检查是否为内容页而非挑战页
        if "Just a moment" in driver.page_source or "Checking your browser" in driver.page_source:
            logger.info("检测到Cloudflare文本，等待验证完成...")
            time.sleep(timeout)  # 给Cloudflare充分时间完成验证
            return True
            
        return False  # 没有检测到Cloudflare挑战
        
    except Exception as e:
        logger.warning(f"等待Cloudflare验证时出错: {e}")
        return False

def extract_origin(name, origins):
    """从名称中提取产地"""
    if not name:
        return None
        
    for origin in origins:
        if origin in name:
            return origin
    return None

def extract_weight(name, description=None):
    """从产品名称或描述中提取重量信息"""
    # 常见的重量单位模式
    weight_patterns = [
        r'(\d+(?:\.\d+)?)\s*[Ll][Bb][Ss]?', # 例如：1lb, 2lbs, 1.5 lbs
        r'(\d+(?:\.\d+)?)\s*[Oo][Zz]',      # 例如：12oz, 16 oz
        r'(\d+(?:\.\d+)?)\s*[Pp][Oo][Uu][Nn][Dd][Ss]?', # 例如：1pound, 2pounds
        r'(\d+(?:\.\d+)?)\s*[Kk][Gg]',      # 例如：1kg, 0.5kg
        r'(\d+(?:\.\d+)?)\s*[Gg][Rr][Aa][Mm][Ss]?', # 例如：500grams, 250gram
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
    
    # Sweet Maria's默认使用1磅包装
    return {"value": 1, "unit": "lb"}

def run_spider():
    """运行Sweet Maria's爬虫，使用undetected-chromedriver绕过Cloudflare"""
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # 切换到项目根目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # 确保项目目录在Python路径中
    if project_dir not in sys.path:
        sys.path.append(project_dir)
    
    # 确保结果目录存在
    results_dir = Path(project_dir) / 'results'
    results_dir.mkdir(exist_ok=True)
    
    # 初始化爬虫对象（只用于获取配置）
    spider = SweetMariasSpider()
    
    # 常见产地列表
    origins = [
        'Ethiopia', 'Kenya', 'Colombia', 'Guatemala', 'Costa Rica', 'El Salvador',
        'Honduras', 'Nicaragua', 'Panama', 'Mexico', 'Brazil', 'Peru', 'Burundi',
        'Rwanda', 'Tanzania', 'Uganda', 'Yemen', 'Indonesia', 'Papua New Guinea',
        'East Timor', 'India', 'Sumatra', 'Java', 'Sulawesi'
    ]
    
    try:
        print(f'开始爬取Sweet Maria\'s网站数据，结果将保存到 {results_dir} 目录')
        
        # 初始化undetected-chromedriver
        driver = setup_driver()
        
        # 爬取目标URL
        target_url = spider.start_urls[0]
        
        try:
            # 访问首页，建立会话
            logger.info("访问首页...")
            driver.get("https://www.sweetmarias.com/")
            
            # 等待可能的Cloudflare验证
            cloudflare_detected = wait_for_cloudflare(driver)
            if cloudflare_detected:
                logger.info("已通过Cloudflare验证")
            
            # 随机等待一段时间，模拟真实用户浏览
            time.sleep(random.uniform(5, 8))
            
            # 随机鼠标移动和滚动（模拟用户行为）
            try:
                driver.execute_script("""
                    var event = new MouseEvent('mousemove', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true,
                        'clientX': Math.floor(Math.random() * window.innerWidth),
                        'clientY': Math.floor(Math.random() * window.innerHeight)
                    });
                    document.dispatchEvent(event);
                    
                    // 随机滚动
                    window.scrollBy(0, Math.floor(Math.random() * 300));
                """)
            except Exception as e:
                logger.warning(f"模拟用户行为失败: {e}")
            
            # 访问目标页面
            logger.info(f"访问目标页面: {target_url}")
            driver.get(target_url)
            
            # 再次等待可能的Cloudflare验证
            cloudflare_detected = wait_for_cloudflare(driver)
            if cloudflare_detected:
                logger.info("产品页面已通过Cloudflare验证")
            
            # 等待页面加载完成
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            
            # 再次随机等待，确保JavaScript加载完成
            time.sleep(random.uniform(3, 6))
            
            # 随机向下滚动几次，模拟用户浏览行为
            for _ in range(random.randint(3, 6)):
                scroll_amount = random.randint(300, 800)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(1, 2.5))
            
            logger.info("页面加载完成，准备解析内容")
            
            # 保存页面源码用于调试
            debug_file = results_dir / "sweet_marias_debug.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info(f"保存HTML到 {debug_file}")
            
            # 使用BeautifulSoup解析页面
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 提取商品信息
            products = []
            product_items = soup.select('li.product-item')
            logger.info(f"找到 {len(product_items)} 个产品元素")
            
            if not product_items:
                logger.warning("未找到产品元素，尝试查找替代元素")
                # 检查页面上的主要元素以帮助调试
                main_elements = soup.select('main, .main, .page-main, .products, .product-grid')
                for i, elem in enumerate(main_elements):
                    logger.info(f"主要元素 {i+1}: {elem.name} - 类: {elem.get('class', [])}")
                
                # 尝试直接从页面上获取产品元素
                try:
                    product_elements = driver.find_elements(By.CSS_SELECTOR, '.product-item, .product-grid > li, .item.product')
                    if product_elements:
                        logger.info(f"通过WebDriver直接找到 {len(product_elements)} 个产品元素")
                        # 循环处理每个产品
                        for product_elem in product_elements:
                            try:
                                # 获取产品HTML并用BeautifulSoup解析
                                product_html = product_elem.get_attribute('outerHTML')
                                product = BeautifulSoup(product_html, 'html.parser')
                                
                                # 提取基本信息
                                name_elem = product.select_one('.product-item-link, .product-name')
                                if name_elem:
                                    name = name_elem.text.strip()
                                    
                                    # 提取价格
                                    price_elem = product.select_one('.price-container .price, .price')
                                    price = price_elem.text.strip() if price_elem else None
                                    if price:
                                        price = price.replace('$', '').strip()
                                        try:
                                            price = float(price)
                                        except ValueError:
                                            logger.warning(f"无法解析价格: {price}")
                                    
                                    # 提取URL
                                    url_elem = product.select_one('a.product-item-link, a.product-name, a[href]')
                                    url = url_elem.get('href') if url_elem else None
                                    
                                    # 提取产地
                                    origin = extract_origin(name, origins)
                                    
                                    # 提取重量
                                    weight = extract_weight(name, product.text)
                                    
                                    # 创建产品数据
                                    product_data = {
                                        'name': name,
                                        'price': price,
                                        'currency': 'USD',
                                        'supplier': 'Sweet Marias',
                                        'url': url,
                                        'updated_at': datetime.now().strftime('%Y-%m-%d'),
                                        'weight': weight
                                    }
                                    
                                    if origin:
                                        product_data['origin'] = origin
                                    
                                    products.append(product_data)
                                    logger.info(f"提取产品: {name}")
                            except Exception as e:
                                logger.error(f"解析单个产品元素出错: {e}")
                except Exception as e:
                    logger.error(f"尝试替代方法获取产品出错: {e}")
            
            # 如果通过选择器找到了产品，则处理
            for product in product_items:
                try:
                    # 提取基本信息
                    name_elem = product.select_one('.product-item-link')
                    name = name_elem.text.strip() if name_elem else None
                    
                    # 提取价格
                    price_elem = product.select_one('.price-container .price')
                    price = price_elem.text.strip() if price_elem else None
                    if price:
                        price = price.replace('$', '').strip()
                        try:
                            price = float(price)
                        except ValueError:
                            logger.warning(f"无法解析价格: {price}")
                    
                    # 提取URL
                    url = name_elem.get('href') if name_elem else None
                    
                    # 提取产地
                    origin = extract_origin(name, origins)
                    
                    # 提取重量
                    weight = extract_weight(name, product.text)
                    
                    # 创建产品数据
                    product_data = {
                        'name': name,
                        'price': price,
                        'currency': 'USD',
                        'supplier': 'Sweet Marias',
                        'url': url,
                        'updated_at': datetime.now().strftime('%Y-%m-%d'),
                        'weight': weight
                    }
                    
                    if origin:
                        product_data['origin'] = origin
                    
                    products.append(product_data)
                    logger.info(f"提取产品: {name}")
                    
                except Exception as e:
                    logger.error(f"解析产品出错: {e}")
            
            # 保存结果
            if products:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = results_dir / f"sweet_marias_{timestamp}.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
                
                logger.info(f"已保存 {len(products)} 个产品到 {filename}")
            else:
                logger.warning("未找到任何产品数据")
                
        except Exception as e:
            logger.error(f"抓取过程出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            # 确保关闭浏览器
            logger.info("关闭WebDriver")
            driver.quit()
        
        print('爬取完成')
        
    except Exception as e:
        logger.error(f"运行爬虫出错: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    run_spider() 