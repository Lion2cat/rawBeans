import os
import sys
import json
import glob
import logging
from datetime import datetime
from pathlib import Path
import difflib


def setup_logging():
    """设置日志配置"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler("merge_coffee_results.log")
    ]
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def get_latest_files(results_dir, prefix_list):
    """获取每个前缀的最新文件"""
    latest_files = {}
    
    for prefix in prefix_list:
        # 先尝试找JSON文件
        json_pattern = f"{prefix}_*.json"
        json_files = glob.glob(str(results_dir / json_pattern))
        
        if json_files:
            latest_file = max(json_files, key=os.path.getmtime)
            latest_files[prefix] = latest_file
            logging.info(f"找到 {prefix} 的最新JSON文件: {os.path.basename(latest_file)}")
        else:
            # 如果找不到JSON文件，尝试找HTML调试文件
            html_pattern = f"{prefix}_debug.html"
            html_files = glob.glob(str(results_dir / html_pattern))
            
            if html_files and len(html_files) > 0:
                latest_file = max(html_files, key=os.path.getmtime)
                logging.info(f"找到 {prefix} 的HTML调试文件: {os.path.basename(latest_file)}")
                logging.warning(f"没有找到 {prefix} 的JSON文件，将尝试从HTML中提取数据")
                
                # 这里需要添加从HTML解析数据的逻辑，暂时返回空列表
                latest_files[prefix] = latest_file
            else:
                logging.warning(f"未找到任何 {prefix} 的文件")
    
    return latest_files


def load_data(file_path):
    """从文件加载数据"""
    # 检查文件类型
    if file_path.endswith('.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info(f"从 {os.path.basename(file_path)} 加载了 {len(data)} 条记录")
                return data
        except Exception as e:
            logging.error(f"加载JSON文件 {file_path} 时出错: {e}")
            return []
    elif file_path.endswith('.html'):
        # 如果是HTML文件，尝试解析出产品数据
        logging.info(f"尝试从HTML文件 {os.path.basename(file_path)} 解析数据")
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取产品信息 - 这里需要根据具体HTML结构调整
            products = []
            
            # 获取供应商名称
            supplier = "Unknown"
            if "sweet_marias" in os.path.basename(file_path).lower():
                supplier = "Sweet Maria's"
            elif "coffee_shrub" in os.path.basename(file_path).lower():
                supplier = "Coffee Shrub"
            
            # 尝试多种产品选择器
            product_selectors = [
                '.product-item', '.grid__item', '.product-card',
                '.product', '.product-container', '.card', 
                'article', '.coffee-item', '.results-grid .product'
            ]
            
            found_products = False
            for selector in product_selectors:
                product_elements = soup.select(selector)
                if product_elements and len(product_elements) > 0:
                    logging.info(f"使用选择器 '{selector}' 在HTML中找到 {len(product_elements)} 个产品")
                    
                    for product_elem in product_elements:
                        try:
                            # 尝试提取名称
                            name = None
                            name_selectors = [
                                '.product-title', '.title', 'h2', 'h3', 
                                '.name', '.product-name', 'a.card-title'
                            ]
                            
                            for name_selector in name_selectors:
                                name_elem = product_elem.select_one(name_selector)
                                if name_elem and name_elem.text.strip():
                                    name = name_elem.text.strip()
                                    break
                            
                            # 如果没找到名称，尝试使用产品元素的文本
                            if not name:
                                name = product_elem.text.strip().split('\n')[0]
                            
                            # 如果名称是导航元素，跳过
                            if not name or name.lower() in ['shop all', 'home', 'menu', 'cart']:
                                continue
                                
                            # 提取价格
                            price = None
                            price_selectors = [
                                '.price', '.product-price', '.money',
                                '.price-item', '.current-price'
                            ]
                            
                            for price_selector in price_selectors:
                                price_elem = product_elem.select_one(price_selector)
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
                            url_elements = product_elem.select('a')
                            if url_elements:
                                for url_elem in url_elements:
                                    if 'href' in url_elem.attrs:
                                        href = url_elem['href']
                                        if 'product' in href or 'collections' in href:
                                            url = href
                                            break
                                
                                # 如果没找到特定URL，使用第一个
                                if not url and url_elements and 'href' in url_elements[0].attrs:
                                    url = url_elements[0]['href']
                            
                            # 确保URL是完整的
                            if url and url.startswith('/'):
                                if "sweet_marias" in os.path.basename(file_path).lower():
                                    url = f"https://www.sweetmarias.com{url}"
                                elif "coffee_shrub" in os.path.basename(file_path).lower():
                                    url = f"https://www.coffeeshrub.com{url}"
                            
                            # 提取产地
                            origin = None
                            origins = [
                                'Ethiopia', 'Kenya', 'Colombia', 'Guatemala', 
                                'Costa Rica', 'El Salvador', 'Honduras', 'Nicaragua', 
                                'Panama', 'Mexico', 'Brazil', 'Peru', 'Burundi',
                                'Rwanda', 'Tanzania', 'Uganda', 'Yemen', 'Indonesia', 
                                'Papua New Guinea', 'East Timor', 'India'
                            ]
                            
                            if name:
                                for o in origins:
                                    if o.lower() in name.lower():
                                        origin = o
                                        break
                            
                            # 创建产品数据
                            product_data = {
                                'name': name,
                                'supplier': supplier,
                                'updated_at': datetime.now().strftime('%Y-%m-%d')
                            }
                            
                            if price:
                                product_data['price'] = price
                                product_data['currency'] = 'USD'
                                
                            if url:
                                product_data['url'] = url
                                
                            if origin:
                                product_data['origin'] = origin
                            
                            products.append(product_data)
                            found_products = True
                            
                        except Exception as e:
                            logging.error(f"解析产品时出错: {e}")
                    
                    if found_products:
                        break
            
            logging.info(f"从HTML文件中提取了 {len(products)} 个产品")
            return products
            
        except ImportError:
            logging.error("无法导入BeautifulSoup库，请安装: pip install beautifulsoup4")
            return []
        except Exception as e:
            logging.error(f"从HTML解析数据时出错: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return []
    else:
        logging.error(f"不支持的文件类型: {file_path}")
        return []


def normalize_product(product):
    """标准化产品数据，确保关键字段存在"""
    # 确保所有关键字段都有默认值
    normalized = {
        'name': product.get('name', '').strip() if product.get('name') else '',
        'supplier': product.get('supplier', '').strip() if product.get('supplier') else '',
        'price': product.get('price', None),
        'currency': product.get('currency', 'USD'),
        'origin': product.get('origin', '').strip() if product.get('origin') else '',
        'url': product.get('url', '').strip() if product.get('url') else '',
        'updated_at': product.get('updated_at', datetime.now().strftime('%Y-%m-%d'))
    }
    
    # 添加其他可能存在的字段
    for key, value in product.items():
        if key not in normalized:
            normalized[key] = value
    
    return normalized


def is_duplicate(product1, product2, similarity_threshold=0.8):
    """检查两个产品是否重复"""
    # 如果供应商不同，不认为是重复
    if product1['supplier'] != product2['supplier']:
        return False
    
    # 检查名称相似度
    name_similarity = difflib.SequenceMatcher(None, product1['name'].lower(), product2['name'].lower()).ratio()
    
    # 如果名称相似度高，还要检查价格
    if name_similarity >= 0.9:
        # 获取价格，如果价格不存在则不比较价格
        price1 = product1.get('price')
        price2 = product2.get('price')
        
        # 如果两个产品都有价格，比较价格是否相同或接近
        if price1 is not None and price2 is not None:
            # 价格差异不超过5%视为相同
            price_diff = abs(price1 - price2) / max(price1, price2)
            return price_diff <= 0.05
        
        # 如果至少一个没有价格，只看名称相似度
        return True
    
    return False


def merge_data(data_sources):
    """合并多个数据源，并去除重复"""
    merged_data = []
    
    # 用于跟踪已添加的产品，避免重复
    added_products = set()
    
    for source_name, products in data_sources.items():
        logging.info(f"处理来源: {source_name}, 产品数量: {len(products)}")
        
        for product in products:
            # 标准化产品数据
            normalized_product = normalize_product(product)
            
            # 检查是否重复
            is_duplicate_product = False
            for existing_product in merged_data:
                if is_duplicate(normalized_product, existing_product):
                    is_duplicate_product = True
                    logging.debug(f"找到重复产品: {normalized_product['name']} 与 {existing_product['name']}")
                    break
            
            # 如果不是重复产品，则添加到合并列表
            if not is_duplicate_product:
                merged_data.append(normalized_product)
                added_products.add(normalized_product['name'])
            
    logging.info(f"合并后总产品数: {len(merged_data)}")
    return merged_data


def save_merged_data(merged_data, results_dir):
    """保存合并后的数据到JSON文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = results_dir / f"merged_coffee_data_{timestamp}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        logging.info(f"已保存 {len(merged_data)} 条合并记录到 {output_file}")
        return output_file
    except Exception as e:
        logging.error(f"保存合并数据时出错: {e}")
        return None


def run_merge():
    """运行合并处理"""
    logger = setup_logging()
    logger.info("开始合并Coffee Shrub和Sweet Maria's数据")
    
    # 切换到项目根目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # 确保项目目录在Python路径中
    if project_dir not in sys.path:
        sys.path.append(project_dir)
    
    # 结果目录
    results_dir = Path(project_dir) / 'results'
    if not results_dir.exists():
        results_dir.mkdir(exist_ok=True)
        logger.info(f"创建结果目录: {results_dir}")
    
    # 获取最新的数据文件
    prefix_list = ['sweet_marias', 'coffee_shrub']
    latest_files = get_latest_files(results_dir, prefix_list)
    
    if not latest_files:
        logger.error("未找到任何数据文件")
        return
    
    # 加载数据
    data_sources = {}
    for prefix, file_path in latest_files.items():
        data = load_data(file_path)
        if data:
            data_sources[prefix] = data
    
    if not data_sources:
        logger.error("没有有效的数据可合并")
        return
    
    # 合并数据
    merged_data = merge_data(data_sources)
    
    # 保存合并数据
    if merged_data:
        output_file = save_merged_data(merged_data, results_dir)
        if output_file:
            logger.info(f"合并完成! 文件保存到: {output_file}")
    else:
        logger.warning("没有数据可保存")
    
    logger.info("合并处理完成")


if __name__ == '__main__':
    run_merge() 