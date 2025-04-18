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
from selenium.webdriver.common.action_chains import ActionChains

# BeautifulSoup用于解析页面
from bs4 import BeautifulSoup

# 添加导入爬虫类（只用于获取常量）
try:
    from scrapers.spiders.coffee_shrub_spider import CoffeeShrubSpider
except ImportError:
    # 如果无法导入，不影响脚本执行
    pass

def setup_driver():
    """配置undetected-chromedriver，绕过Cloudflare防护"""
    try:
        # 保持兼容性的Chrome版本，避免版本不匹配问题
        # 如果遇到版本错误，请调整此值为您系统中安装的Chrome版本
        version_main = None  # 让undetected-chromedriver自动检测版本
        
        options = uc.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # 设置更真实的用户代理
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        
        # 禁用自动化标志
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # 禁用扩展
        options.add_argument("--disable-extensions")
        
        # 启用JavaScript
        options.add_argument("--enable-javascript")
        
        # 使用无痕模式
        options.add_argument("--incognito")
        
        # 初始化undetected-chromedriver
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=version_main)
        
        # 设置页面加载超时
        driver.set_page_load_timeout(120)
        # 设置脚本超时
        driver.set_script_timeout(90)
        
        # 清除cookies
        driver.delete_all_cookies()
        
        return driver
    except Exception as e:
        logging.error(f"初始化Chrome驱动失败: {e}")
        # 尝试不带options参数
        try:
            driver = uc.Chrome(use_subprocess=True)
            driver.set_page_load_timeout(120)
            return driver
        except Exception as e2:
            logging.error(f"再次尝试初始化Chrome驱动失败: {e2}")
            raise

def wait_for_cloudflare(driver, timeout=120):
    """等待Cloudflare验证完成"""
    logger = logging.getLogger(__name__)
    logger.info("等待Cloudflare验证...")
    
    start_time = time.time()
    
    # 先确保页面至少有基本加载
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except:
        logger.warning("等待页面加载基本元素超时")
    
    # 检查是否存在Cloudflare挑战页面元素
    cloudflare_selectors = [
        "div.cf-browser-verification", 
        "#cf-please-wait",
        "iframe[src*='challenges.cloudflare.com']",
        ".cf-error-code",
        "#challenge-running",
        "#challenge-form",
        "#cf-challenge-running"
    ]
    
    cloudflare_texts = [
        "Just a moment", 
        "Checking your browser",
        "Please wait",
        "Please turn JavaScript on",
        "Please enable Cookies",
        "DDoS protection by",
        "Cloudflare",
        "Security check"
    ]
    
    # 等待直到超时
    while time.time() - start_time < timeout:
        # 检查是否存在Cloudflare元素
        cloud_element_found = False
        for selector in cloudflare_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logger.info(f"检测到Cloudflare挑战元素: {selector}")
                cloud_element_found = True
                # 等待一段时间，让Cloudflare通过
                time.sleep(10)  
                break
        
        if not cloud_element_found:
            # 检查是否存在Cloudflare文本
            page_text = driver.page_source.lower()
            cf_detected = False
            for text in cloudflare_texts:
                if text.lower() in page_text:
                    logger.info(f"检测到Cloudflare文本: '{text}'")
                    cf_detected = True
                    time.sleep(10)  # 等待更长时间
                    break
            
            if not cf_detected:
                # 如果没有检测到Cloudflare元素和文本，检查是否已加载内容
                try:
                    # 检查是否找到产品内容
                    content_selectors = [
                        ".product-item", 
                        ".grid__item", 
                        ".collection-products",
                        ".product-grid", 
                        "main",
                        ".grid"
                    ]
                    
                    for content_selector in content_selectors:
                        content = driver.find_elements(By.CSS_SELECTOR, content_selector)
                        if content and len(content) > 0:
                            logger.info(f"找到页面内容: {content_selector}")
                            time.sleep(5)  # 确保完全加载
                            return True
                    
                    # 如果找不到产品元素但页面看起来已加载，尝试检查基本页面结构
                    if "coffeeshrub" in driver.page_source.lower() and len(driver.page_source) > 5000:
                        logger.info("页面已加载，但未检测到特定内容元素")
                        time.sleep(5)
                        return True
                except Exception as e:
                    logger.warning(f"检查页面内容时出错: {e}")
        
        # 模拟人类交互，帮助通过验证
        try:
            # 随机移动鼠标
            actions = ActionChains(driver)
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            actions.move_by_offset(x, y).perform()
            
            # 随机滚动
            scroll_amount = random.randint(100, 300)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        except:
            pass
        
        # 检查是否已经超过总时间
        elapsed = time.time() - start_time
        if elapsed > timeout - 15:  # 在超时前15秒结束等待
            logger.warning(f"Cloudflare等待即将超时 ({elapsed:.1f}s)")
            break
        
        time.sleep(5)  # 暂停时间增加到5秒
    
    logger.info("Cloudflare等待完成或超时")
    return True

def extract_origin(name, description=None, origins=None):
    """从名称和描述中提取产地"""
    if origins is None:
        origins = [
            'Ethiopia', 'Kenya', 'Colombia', 'Guatemala', 'Costa Rica', 'El Salvador',
            'Honduras', 'Nicaragua', 'Panama', 'Mexico', 'Brazil', 'Peru', 'Burundi',
            'Rwanda', 'Tanzania', 'Uganda', 'Yemen', 'Indonesia', 'Papua New Guinea',
            'East Timor', 'India', 'Sumatra', 'Java', 'Sulawesi'
        ]
    
    # 先从名称中提取
    if name:
        for origin in origins:
            if origin.lower() in name.lower():
                return origin
    
    # 如果未找到，从描述中提取
    if description:
        for origin in origins:
            if origin.lower() in description.lower():
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
    
    # Coffee Shrub默认使用50磅包装
    return {"value": 50, "unit": "lb"}

def run_spider():
    """运行Coffee Shrub爬虫，使用undetected-chromedriver绕过Cloudflare"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("coffee_shrub_spider.log")
        ]
    )
    logger = logging.getLogger(__name__)
    
    # 记录开始时间
    start_time = time.time()
    
    # 切换到项目根目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # 确保项目目录在Python路径中
    if project_dir not in sys.path:
        sys.path.append(project_dir)
    
    # 确保结果目录存在
    results_dir = Path(project_dir) / 'results'
    results_dir.mkdir(exist_ok=True)
    
    # 目标URL
    target_url = "https://www.coffeeshrub.com/green-coffee.html?product_list_limit=all&sm_status=1"
    
    # 常见产地列表
    origins = [
        'Ethiopia', 'Kenya', 'Colombia', 'Guatemala', 'Costa Rica', 'El Salvador',
        'Honduras', 'Nicaragua', 'Panama', 'Mexico', 'Brazil', 'Peru', 'Burundi',
        'Rwanda', 'Tanzania', 'Uganda', 'Yemen', 'Indonesia', 'Papua New Guinea',
        'East Timor', 'India', 'Sumatra', 'Java', 'Sulawesi'
    ]
    
    # 保存信息的产品列表
    products = []
    driver = None
    
    try:
        logger.info(f'开始爬取Coffee Shrub网站数据，结果将保存到 {results_dir} 目录')
        
        # 初始化undetected-chromedriver
        driver = setup_driver()
        
        # 添加JavaScript代码来减轻指纹识别
        stealth_js = """
        // 隐藏webdriver属性
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        
        // 修改userAgent使其看起来更真实
        Object.defineProperty(navigator, 'userAgent', {
            get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        });
        
        // 修改语言偏好
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'zh-CN'],
        });
        
        // 隐藏硬件并发
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
        });
        
        // 隐藏Chrome对象属性
        if (window.chrome) {
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {},
            };
        }
        """
        
        try:
            driver.execute_script(stealth_js)
            logger.info("应用了stealth JS脚本")
        except Exception as e:
            logger.warning(f"应用stealth JS失败: {e}")
        
        # 直接访问目标页面，但先预热浏览器
        logger.info("正在预热浏览器...")
        try:
            # 首先访问Google，让浏览器"热身"
            driver.get("https://www.google.com")
            time.sleep(random.uniform(3, 6))
            
            # 然后访问目标网站首页
            logger.info("访问Coffee Shrub首页...")
            driver.get("https://www.coffeeshrub.com/")
            
            # 等待可能的Cloudflare验证，增加超时时间
            if not wait_for_cloudflare(driver, timeout=180):
                logger.warning("无法通过Cloudflare验证，但将继续尝试...")
            
            # 随机等待一段时间，模拟真实用户浏览
            time.sleep(random.uniform(5, 8))
            
            # 随机鼠标移动和滚动（模拟用户行为）
            logger.info("模拟用户交互行为...")
            try:
                # 创建ActionChains
                actions = ActionChains(driver)
                
                # 随机鼠标移动
                for _ in range(5):
                    x = random.randint(100, 800)
                    y = random.randint(100, 600)
                    actions.move_by_offset(x, y).perform()
                    time.sleep(random.uniform(1.5, 3.0))
                    
                # 随机滚动
                for _ in range(3):
                    scroll_amount = random.randint(100, 700)
                    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                    time.sleep(random.uniform(2.0, 4.0))
                    
            except Exception as e:
                logger.warning(f"模拟用户行为失败: {e}")
        except Exception as e:
            logger.error(f"预热浏览器失败: {e}")
            # 如果预热失败，也继续执行
        
        # 访问目标页面
        logger.info(f"访问目标页面: {target_url}")
        max_retries = 3
        page_loaded = False
        
        for retry in range(max_retries):
            try:
                driver.get(target_url)
                
                # 等待可能的Cloudflare验证，增加超时时间
                if not wait_for_cloudflare(driver, timeout=180):
                    logger.warning("可能无法通过Cloudflare验证，但将继续尝试...")
                
                # 等待页面加载完成 - 尝试不同的选择器
                selectors_to_try = [
                    ".product-item", 
                    ".grid__item", 
                    ".collection-products", 
                    ".product-grid",
                    "main .grid",
                    "main"
                ]
                
                for selector in selectors_to_try:
                    try:
                        WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"页面加载完成，找到元素: {selector}")
                        page_loaded = True
                        break
                    except TimeoutException:
                        continue
                
                if page_loaded:
                    break
                    
                # 如果没有找到常规元素，但页面已加载（判断页面源码长度和是否包含关键词）
                if "coffeeshrub" in driver.page_source.lower() and len(driver.page_source) > 10000:
                    logger.info("页面已加载，但未检测到产品元素")
                    page_loaded = True
                    break
                    
                if retry < max_retries - 1:
                    logger.warning(f"尝试 {retry+1}/{max_retries} 失败，重试中...")
                    # 关闭并重新打开浏览器
                    driver.quit()
                    driver = setup_driver()
                    time.sleep(20)  # 等待时间延长
                    
            except Exception as e:
                logger.error(f"加载页面时出错: {e}")
                if retry < max_retries - 1:
                    logger.warning(f"将重试 {retry+2}/{max_retries}...")
                    driver.quit()
                    driver = setup_driver()
                    time.sleep(20)
        
        if not page_loaded:
            logger.error("多次尝试后页面仍然无法加载，将尝试解析可能不完整的页面")
        
        # 额外等待JS加载
        logger.info("等待JS完全加载...")
        time.sleep(20)
        
        # 随机向下滚动几次，模拟用户浏览行为
        logger.info("模拟用户浏览行为...")
        try:
            for _ in range(random.randint(5, 10)):
                scroll_amount = random.randint(300, 800)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(2.5, 5.0))
                
                # 偶尔向上滚动一点，更像真人
                if random.random() < 0.3:
                    up_scroll = random.randint(50, 200)
                    driver.execute_script(f"window.scrollBy(0, -{up_scroll});")
                    time.sleep(random.uniform(1.0, 2.5))
        except Exception as e:
            logger.warning(f"滚动页面时出错: {e}")
        
        logger.info("页面加载完成，准备解析内容")
        
        # 保存页面源码用于调试
        try:
            debug_file = results_dir / "coffee_shrub_debug.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info(f"保存HTML到 {debug_file}")
        except Exception as e:
            logger.error(f"保存HTML调试文件时出错: {e}")
        
        # 尝试多种产品选择器 - 先尝试用Selenium
        product_selectors = [
            '.product-item',
            '.grid__item .product',
            '.grid-view-item',
            '.grid__item',
            '.product-collection-grid .grid__item',
            'ul.grid li',
            '.collection .grid__item',
            '.product-card',
            'article.grid__item',
            '.product-list li',
            '.featured-collection-grid__item',
            'main .grid li'
        ]
        
        # 使用Selenium直接查找产品元素
        found_products = False
        for selector in product_selectors:
            try:
                logger.info(f"尝试使用选择器: {selector}")
                product_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if product_elements:
                    logger.info(f"使用选择器 '{selector}' 找到 {len(product_elements)} 个产品")
                    
                    for product_elem in product_elements:
                        try:
                            # 尝试获取产品名称
                            name_selectors = [
                                '.product-title', '.product-item-title', '.title', 
                                '.product-item__title', '.name-title', '.product-card__title',
                                'h2', 'h3', 'h4', '.grid-product__title', 'h1', 'a.full-unstyled-link',
                                '.card__heading', 'a'
                            ]
                            name = None
                            for name_selector in name_selectors:
                                try:
                                    name_elems = product_elem.find_elements(By.CSS_SELECTOR, name_selector)
                                    if name_elems:
                                        name = name_elems[0].text.strip()
                                        if name:
                                            break
                                except:
                                    continue
                            
                            if not name:
                                # 如果找不到名称，尝试找任何可能的文本
                                try:
                                    name = product_elem.text.split('\n')[0].strip()
                                except:
                                    pass
                                    
                            if not name or name.lower() in ['shop all', 'home', 'menu', 'cart']:
                                # 如果仍然找不到名称或名称是导航元素，跳过这个产品
                                continue
                                
                            # 尝试获取价格
                            price_selectors = [
                                '.price', '.product-price', '.product-item-price', 
                                '.price__sale', '.price-item', '.money', '.product-price__price',
                                '.product-card__price', '.price__current', '.price-item--regular'
                            ]
                            price = None
                            for price_selector in price_selectors:
                                try:
                                    price_elems = product_elem.find_elements(By.CSS_SELECTOR, price_selector)
                                    for price_elem in price_elems:
                                        price_text = price_elem.text.strip()
                                        if price_text and ('$' in price_text or 'USD' in price_text):
                                            # 清理价格文本，提取数值
                                            price_text = price_text.replace('$', '').replace('USD', '').strip()
                                            # 如果有多个价格（如优惠价），取第一个
                                            if ' ' in price_text:
                                                price_text = price_text.split(' ')[0]
                                            try:
                                                price = float(price_text)
                                                break
                                            except ValueError:
                                                logger.warning(f"无法解析价格: {price_text}")
                                    if price is not None:
                                        break
                                except:
                                    continue
                            
                            # 尝试获取URL
                            url = None
                            try:
                                # 首先尝试从产品元素找a标签
                                a_elements = product_elem.find_elements(By.TAG_NAME, 'a')
                                if a_elements:
                                    for a_elem in a_elements:
                                        href = a_elem.get_attribute('href')
                                        if href and ('product' in href or 'collections' in href):
                                            url = href
                                            break
                                    # 如果没找到合适的链接，使用第一个
                                    if not url and a_elements:
                                        url = a_elements[0].get_attribute('href')
                            except Exception as e:
                                logger.warning(f"获取产品URL时出错: {e}")
                            
                            # 创建产品数据
                            product_data = {
                                'name': name,
                                'supplier': 'Coffee Shrub',
                                'updated_at': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            if price is not None:
                                product_data['price'] = price
                                product_data['currency'] = 'USD'
                                
                            if url:
                                # 确保URL是完整的
                                if url.startswith('/'):
                                    url = f"https://www.coffeeshrub.com{url}"
                                product_data['url'] = url
                            
                            # 提取产地
                            origin = extract_origin(name, None, origins)
                            if origin:
                                product_data['origin'] = origin
                            
                            # 设置默认重量为50磅
                            product_data['weight'] = {"value": 50, "unit": "lb"}
                            
                            products.append(product_data)
                            logger.info(f"提取产品: {name}")
                            found_products = True
                            
                        except Exception as e:
                            logger.error(f"处理单个产品时出错: {str(e)}")
                            
                    # 如果找到并处理了产品，就不需要尝试其他选择器
                    if found_products:
                        break
            except Exception as e:
                logger.error(f"使用选择器 '{selector}' 查找产品时出错: {str(e)}")
        
        # 如果未找到产品，尝试使用BeautifulSoup作为备选
        if not products:
            logger.info("未通过Selenium找到产品，尝试使用BeautifulSoup解析")
            
            try:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                for selector in product_selectors:
                    product_items = soup.select(selector)
                    if product_items:
                        logger.info(f"使用BeautifulSoup选择器 '{selector}' 找到 {len(product_items)} 个产品")
                        
                        for product in product_items:
                            try:
                                # 尝试多种可能的选择器来提取产品名称
                                name_selectors = [
                                    '.product-title', '.product-item-title', '.title', 
                                    '.product-item__title', '.name-title', '.product-card__title',
                                    'h2', 'h3', 'h4', '.grid-product__title', 'h1', 'a.full-unstyled-link',
                                    '.card__heading', 'a'
                                ]
                                name = None
                                for name_selector in name_selectors:
                                    name_elem = product.select_one(name_selector)
                                    if name_elem:
                                        name = name_elem.text.strip()
                                        if name:
                                            break
                                
                                if not name:
                                    # 如果找不到名称，尝试获取产品的第一行文本
                                    if product.text:
                                        name = product.text.split('\n')[0].strip()
                                
                                if not name or name.lower() in ['shop all', 'home', 'menu', 'cart']:
                                    # 如果仍然找不到名称或名称是导航元素，跳过这个产品
                                    continue
                                    
                                # 提取价格
                                price_selectors = [
                                    '.price', '.product-price', '.product-item-price', 
                                    '.price__sale', '.price-item', '.money', '.product-price__price',
                                    '.product-card__price', '.price__current', '.price-item--regular'
                                ]
                                price = None
                                for price_selector in price_selectors:
                                    price_elem = product.select_one(price_selector)
                                    if price_elem:
                                        price_text = price_elem.text.strip()
                                        if price_text and ('$' in price_text or 'USD' in price_text):
                                            price_text = price_text.replace('$', '').replace('USD', '').strip()
                                            if ' ' in price_text:
                                                price_text = price_text.split(' ')[0]
                                            try:
                                                price = float(price_text)
                                                break
                                            except ValueError:
                                                pass
                                
                                # 提取URL
                                url = None
                                a_elems = product.select('a')
                                if a_elems:
                                    for a_elem in a_elems:
                                        if 'href' in a_elem.attrs:
                                            href = a_elem['href']
                                            if 'product' in href or 'collections' in href:
                                                url = href
                                                break
                                    # 如果没找到合适的链接，使用第一个
                                    if not url and a_elems and 'href' in a_elems[0].attrs:
                                        url = a_elems[0]['href']
                                
                                # 创建产品数据
                                product_data = {
                                    'name': name,
                                    'supplier': 'Coffee Shrub',
                                    'updated_at': datetime.now().strftime('%Y-%m-%d')
                                }
                                
                                if price is not None:
                                    product_data['price'] = price
                                    product_data['currency'] = 'USD'
                                    
                                if url:
                                    # 确保URL是完整的
                                    if url.startswith('/'):
                                        url = f"https://www.coffeeshrub.com{url}"
                                    product_data['url'] = url
                                
                                # 提取产地
                                origin = extract_origin(name, None, origins)
                                if origin:
                                    product_data['origin'] = origin
                                
                                # 设置默认重量为50磅
                                product_data['weight'] = {"value": 50, "unit": "lb"}
                                
                                products.append(product_data)
                                logger.info(f"使用BeautifulSoup提取产品: {name}")
                                
                            except Exception as e:
                                logger.error(f"使用BeautifulSoup解析产品出错: {str(e)}")
                        
                        # 如果找到并处理了产品，就不需要尝试其他选择器
                        if products:
                            break
            except Exception as e:
                logger.error(f"BeautifulSoup解析时出错: {e}")
        
        # 记录总运行时间
        total_time = time.time() - start_time
        logger.info(f"爬虫任务耗时 {total_time:.2f} 秒")
        
        # 保存结果
        if products:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = results_dir / f"coffee_shrub_{timestamp}.json"
            
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
        if driver:
            logger.info("关闭WebDriver")
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"关闭WebDriver时出错: {e}")

if __name__ == '__main__':
    run_spider() 