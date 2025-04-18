import os
import json
import requests
import pandas as pd
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

def get_usd_to_cny_rate():
    """获取实时美元兑人民币汇率"""
    try:
        # 使用ExchangeRate-API获取汇率
        response = requests.get("https://open.er-api.com/v6/latest/USD")
        data = response.json()
        if response.status_code == 200 and 'rates' in data:
            cny_rate = data['rates']['CNY']
            print(f"获取到当前汇率: 1 USD = {cny_rate} CNY")
            return cny_rate
        else:
            print("无法获取汇率数据，使用默认汇率(7.1)")
            return 7.1  # 默认汇率
    except Exception as e:
        print(f"获取汇率时出错: {e}，使用默认汇率(7.1)")
        return 7.1  # 出错时使用默认汇率

def load_coffee_data(file_path):
    """从合并的JSON文件加载咖啡数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"从{file_path}加载了{len(data)}个咖啡产品")
            
            # 确保每个Coffee Shrub产品都有正确的50磅重量
            for product in data:
                if product.get('supplier') and 'Coffee Shrub' in product.get('supplier'):
                    # 设置重量为50磅
                    product['weight'] = {'value': 50, 'unit': 'lb'}
                    
            return data
    except Exception as e:
        print(f"加载数据出错: {e}")
        return []

def categorize_by_origin(data):
    """按产地分类数据"""
    categorized = {}
    
    # 按照原产地分类
    for product in data:
        origin = product.get('origin', '')
        if not origin:
            origin = "未知产地"
        
        if origin not in categorized:
            categorized[origin] = []
        
        categorized[origin].append(product)
    
    # 按产地名称排序
    return dict(sorted(categorized.items()))

def add_cny_prices(data, exchange_rate):
    """为每个产品添加人民币价格和单价信息"""
    for product in data:
        # 转换人民币价格
        price_usd = product.get('price')
        if price_usd is not None:
            # 转换为人民币并保留2位小数
            price_cny = round(price_usd * exchange_rate, 2)
            product['price_cny'] = price_cny
        else:
            product['price_cny'] = None
        
        # 添加重量信息（如果没有）
        supplier = product.get('supplier', '')
        if 'weight' not in product:
            # 根据供应商设置默认重量
            if 'Coffee Shrub' in supplier:
                product['weight'] = {'value': 50, 'unit': 'lb'}
            else:
                product['weight'] = {'value': 1, 'unit': 'lb'}
        elif isinstance(product['weight'], dict) and ('value' not in product['weight'] or 'unit' not in product['weight']):
            # 确保重量信息完整
            if 'Coffee Shrub' in supplier:
                product['weight'] = {'value': 50, 'unit': 'lb'}
            else:
                product['weight'] = {'value': 1, 'unit': 'lb'}
        
        # 计算单价 - 元/kg
        if price_usd is not None:
            weight = product['weight']
            weight_value = weight.get('value', 1)
            weight_unit = weight.get('unit', 'lb').lower()
            
            # 计算每磅价格
            # 首先将总价除以包装重量得到每磅价格
            price_per_lb = price_usd / weight_value
            
            # 将每磅价格转换为每公斤价格 (1公斤 = 2.20462磅)
            # 因为1公斤 = 2.20462磅，所以每公斤价格 = 每磅价格 * 2.20462
            price_per_kg = price_per_lb * 2.20462
            
            # 转换为人民币/公斤
            unit_price_cny_per_kg = round(price_per_kg * exchange_rate, 2)
            
            # 只保留人民币/公斤的单价
            product['unit_price_cny_per_kg'] = unit_price_cny_per_kg
        else:
            product['unit_price_cny_per_kg'] = None
    
    return data

def generate_html_table(categorized_data, exchange_rate):
    """生成HTML格式的表格"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>咖啡生豆价格数据</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #5D4037; text-align: center; }
            h2 { color: #795548; margin-top: 30px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #795548; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            tr:hover { background-color: #ddd; }
            .footer { text-align: center; margin-top: 20px; font-size: 0.8em; color: #777; }
            .price { text-align: right; }
            .null-price { color: #999; }
        </style>
    </head>
    <body>
        <h1>咖啡生豆价格数据</h1>
        <p>数据更新时间: """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <p>美元兑人民币汇率: """ + str(exchange_rate) + """</p>
    """
    
    # 添加每个产地的表格
    for origin, products in categorized_data.items():
        html += f"<h2>{origin} ({len(products)}个产品)</h2>"
        html += """
        <table>
            <tr>
                <th>供应商</th>
                <th>产品名称</th>
                <th>单价 (元/kg)</th>
                <th>链接</th>
            </tr>
        """
        
        # 按人民币每公斤单价排序（如果单价存在）
        products_sorted = sorted(products, key=lambda x: (x.get('unit_price_cny_per_kg') is None, x.get('unit_price_cny_per_kg', float('inf'))))
        
        for product in products_sorted:
            unit_price_cny_per_kg = product.get('unit_price_cny_per_kg')
            
            # 处理单价可能为空的情况
            if unit_price_cny_per_kg is None:
                unit_price_cny_per_kg_str = '<span class="null-price">暂无单价</span>'
            else:
                unit_price_cny_per_kg_str = f"¥{unit_price_cny_per_kg:.2f}/kg"
            
            # 获取URL和名称，确保它们存在
            url = product.get('url', '#')
            name = product.get('name', '未知产品')
            supplier = product.get('supplier', '未知供应商')
            
            html += f"""
            <tr>
                <td>{supplier}</td>
                <td>{name}</td>
                <td class="price">{unit_price_cny_per_kg_str}</td>
                <td><a href="{url}" target="_blank">查看详情</a></td>
            </tr>
            """
        
        html += "</table>"
    
    # 添加页脚
    html += """
        <div class="footer">
            <p>此数据由咖啡生豆价格监控系统自动生成</p>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_excel(categorized_data, output_path):
    """生成Excel格式的报表"""
    # 创建Excel写入器
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 概览表
        overview_data = []
        for origin, products in categorized_data.items():
            # 计算每个产地的平均单价（忽略空值）
            unit_prices = [p.get('unit_price_cny_per_kg') for p in products if p.get('unit_price_cny_per_kg') is not None]
            avg_unit_price = sum(unit_prices) / len(unit_prices) if unit_prices else None
            
            overview_data.append({
                '产地': origin,
                '产品数量': len(products),
                '平均单价 (元/kg)': avg_unit_price
            })
        
        # 创建概览DataFrame并写入
        overview_df = pd.DataFrame(overview_data)
        overview_df.to_excel(writer, sheet_name='概览', index=False)
        
        # 为每个产地创建单独的表格
        for origin, products in categorized_data.items():
            # 转换为DataFrame
            df = pd.DataFrame(products)
            
            # 选择要显示的列并重命名
            columns = ['supplier', 'name', 'unit_price_cny_per_kg', 'url', 'updated_at']
            
            column_names = {
                'supplier': '供应商',
                'name': '产品名称',
                'unit_price_cny_per_kg': '单价 (元/kg)',
                'url': '链接',
                'updated_at': '更新日期'
            }
            
            # 检查列是否存在
            valid_columns = [col for col in columns if col in df.columns]
            
            # 如果DataFrame为空，创建一个带有正确列的空DataFrame
            if df.empty:
                df = pd.DataFrame(columns=valid_columns)
            else:
                # 只选择有效的列
                df = df[valid_columns]
            
            # 重命名列
            rename_dict = {k: v for k, v in column_names.items() if k in valid_columns}
            df = df.rename(columns=rename_dict)
            
            # 按单价排序
            if '单价 (元/kg)' in df.columns:
                df = df.sort_values(by='单价 (元/kg)', na_position='last')
            
            # 将数据写入Excel
            sheet_name = origin[:31]  # Excel工作表名称限制为31个字符
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 调整列宽
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)  # 限制最大宽度
    
    print(f"Excel报表已保存到 {output_path}")
    return output_path

def send_email(to_email, subject, html_content, attachment_path=None, text_summary=None):
    """发送邮件（包含HTML内容和可选附件）"""
    # 邮件设置 - 需要替换为你的真实邮箱信息
    smtp_server = "smtp.qq.com"  # 例如: smtp.gmail.com, smtp.qq.com
    smtp_port = 465  # QQ邮箱使用SSL加密的端口
    smtp_username = "3539176144@qq.com"
    smtp_password = "wmjhzrcuekoydagd"  # 授权码
    
    try:
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # 添加纯文本摘要（如果提供）
        if text_summary:
            msg.attach(MIMEText(text_summary, 'plain'))
        
        # 添加HTML内容
        msg.attach(MIMEText(html_content, 'html'))
        
        # 添加附件（如果有）
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as file:
                attachment = MIMEApplication(file.read(), Name=os.path.basename(attachment_path))
                attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(attachment)
        
        # 连接并发送邮件 - 使用SSL连接
        import ssl
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        print(f"邮件成功发送至 {to_email}")
        return True
    except Exception as e:
        print(f"发送邮件时出错: {e}")
        return False

def generate_text_summary(categorized_data, exchange_rate):
    """生成纯文本摘要"""
    summary = [
        "咖啡生豆价格数据摘要",
        f"数据更新时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"美元兑人民币汇率: {exchange_rate}\n"
    ]
    
    # 添加每个产地的摘要
    for origin, products in categorized_data.items():
        # 计算平均单价（只考虑有单价的产品）
        unit_prices = [p.get('unit_price_cny_per_kg') for p in products if p.get('unit_price_cny_per_kg') is not None]
        if unit_prices:
            avg_unit_price = sum(unit_prices) / len(unit_prices)
            
            summary.append(f"{origin} ({len(products)}个产品):")
            summary.append(f"  平均单价: ¥{avg_unit_price:.2f}/kg")
            
            # 添加最低单价产品
            min_price_product = min([p for p in products if p.get('unit_price_cny_per_kg') is not None], 
                                   key=lambda x: x.get('unit_price_cny_per_kg'), default=None)
            if min_price_product:
                summary.append(f"  最低单价: ¥{min_price_product.get('unit_price_cny_per_kg'):.2f}/kg - {min_price_product.get('name')} ({min_price_product.get('supplier')})")
            
            # 添加最高单价产品
            max_price_product = max([p for p in products if p.get('unit_price_cny_per_kg') is not None], 
                                   key=lambda x: x.get('unit_price_cny_per_kg'), default=None)
            if max_price_product:
                summary.append(f"  最高单价: ¥{max_price_product.get('unit_price_cny_per_kg'):.2f}/kg - {max_price_product.get('name')} ({max_price_product.get('supplier')})")
            
            summary.append("")
    
    return "\n".join(summary)

if __name__ == "__main__":
    # 找到最新的合并数据文件
    project_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = Path(project_dir) / 'results'
    
    # 获取所有合并的数据文件并按时间排序
    merged_files = list(results_dir.glob("merged_coffee_data_*.json"))
    if not merged_files:
        print("未找到合并数据文件")
        exit(1)
    
    # 选择最新的文件
    latest_file = max(merged_files, key=lambda f: f.stat().st_mtime)
    print(f"使用最新数据文件: {latest_file}")
    
    # 加载数据
    coffee_data = load_coffee_data(latest_file)
    if not coffee_data:
        print("数据加载失败")
        exit(1)
    
    # 获取美元兑人民币汇率
    exchange_rate = get_usd_to_cny_rate()
    
    # 添加人民币价格
    coffee_data = add_cny_prices(coffee_data, exchange_rate)
    
    # 按产地分类数据
    categorized_data = categorize_by_origin(coffee_data)
    
    # 创建输出目录
    reports_dir = Path(project_dir) / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    # 生成时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 生成HTML报表
    html_content = generate_html_table(categorized_data, exchange_rate)
    html_path = reports_dir / f"coffee_report_{timestamp}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML报表已保存到 {html_path}")
    
    # 生成Excel报表
    excel_path = reports_dir / f"coffee_report_{timestamp}.xlsx"
    generate_excel(categorized_data, excel_path)
    
    # 生成纯文本摘要
    text_summary = generate_text_summary(categorized_data, exchange_rate)
    text_path = reports_dir / f"coffee_report_{timestamp}.txt"
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text_summary)
    print(f"文本摘要已保存到 {text_path}")
    
    # 询问是否发送邮件
    send_to_email = input("是否发送报表到邮箱? (y/n): ")
    if send_to_email.lower() == 'y':
        recipient_email = input("请输入收件人邮箱: ")
        send_email(
            to_email=recipient_email,
            subject=f"咖啡生豆价格报表 - {datetime.datetime.now().strftime('%Y-%m-%d')}",
            html_content=html_content,
            text_summary=text_summary,
            attachment_path=excel_path
        )
        
    print("处理完成!") 