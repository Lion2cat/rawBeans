import os
import sys
import time
import schedule
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("coffee_report_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 邮件接收人配置
RECIPIENTS = [
    "877473326@qq.com"  # 替换为你的邮箱
]

def setup_environment():
    """确保环境正确配置"""
    # 切换到项目根目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # 确保项目目录在Python路径中
    if project_dir not in sys.path:
        sys.path.append(project_dir)
    
    # 确保依赖已安装
    try:
        import pandas as pd
        import requests
        logger.info("所有依赖已正确安装")
    except ImportError as e:
        logger.error(f"缺少依赖: {e}. 请运行 'pip install pandas requests openpyxl schedule'")
        sys.exit(1)
    
    return project_dir

def run_scraper(spider_name):
    """运行指定的爬虫"""
    script_name = f"run_{spider_name}_spider.py"
    logger.info(f"运行爬虫: {script_name}")
    
    try:
        result = subprocess.run(
            ["python", script_name],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"爬虫 {script_name} 运行出错: {result.stderr}")
            return False
        
        logger.info(f"爬虫 {script_name} 运行完成")
        return True
    except Exception as e:
        logger.error(f"启动爬虫时出错: {e}")
        return False

def run_merger():
    """合并数据"""
    logger.info("合并爬虫数据")
    
    try:
        result = subprocess.run(
            ["python", "merge_coffee_results.py"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            logger.error(f"合并数据出错: {result.stderr}")
            return False
        
        logger.info("数据合并完成")
        return True
    except Exception as e:
        logger.error(f"合并数据时出错: {e}")
        return False

def generate_and_send_report(recipients):
    """生成报表并发送邮件"""
    logger.info("生成报表并发送邮件")
    
    try:
        # 导入format_coffee_data模块的功能
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        import format_coffee_data
        
        # 找到最新的合并数据文件
        project_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = Path(project_dir) / 'results'
        
        # 获取所有合并的数据文件并按时间排序
        merged_files = list(results_dir.glob("merged_coffee_data_*.json"))
        if not merged_files:
            logger.error("未找到合并数据文件")
            return False
        
        # 选择最新的文件
        latest_file = max(merged_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"使用最新数据文件: {latest_file}")
        
        # 加载数据
        coffee_data = format_coffee_data.load_coffee_data(latest_file)
        if not coffee_data:
            logger.error("数据加载失败")
            return False
        
        # 获取美元兑人民币汇率
        exchange_rate = format_coffee_data.get_usd_to_cny_rate()
        
        # 添加人民币价格
        coffee_data = format_coffee_data.add_cny_prices(coffee_data, exchange_rate)
        
        # 按产地分类数据
        categorized_data = format_coffee_data.categorize_by_origin(coffee_data)
        
        # 创建输出目录
        reports_dir = Path(project_dir) / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成HTML报表
        html_content = format_coffee_data.generate_html_table(categorized_data, exchange_rate)
        html_path = reports_dir / f"coffee_report_{timestamp}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML报表已保存到 {html_path}")
        
        # 生成Excel报表
        excel_path = reports_dir / f"coffee_report_{timestamp}.xlsx"
        format_coffee_data.generate_excel(categorized_data, excel_path)
        
        # 生成纯文本摘要
        text_summary = format_coffee_data.generate_text_summary(categorized_data, exchange_rate)
        text_path = reports_dir / f"coffee_report_{timestamp}.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_summary)
        logger.info(f"文本摘要已保存到 {text_path}")
        
        # 发送邮件给所有收件人
        for recipient in recipients:
            success = format_coffee_data.send_email(
                to_email=recipient,
                subject=f"咖啡生豆价格报表 - {datetime.now().strftime('%Y-%m-%d')}",
                html_content=html_content,
                text_summary=text_summary,
                attachment_path=excel_path
            )
            if success:
                logger.info(f"成功发送报表至 {recipient}")
            else:
                logger.error(f"发送报表至 {recipient} 失败")
        
        return True
    except Exception as e:
        logger.error(f"生成或发送报表时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_full_process():
    """运行完整的数据收集和报表生成流程"""
    logger.info("开始完整的数据收集和报表生成流程")
    
    # 运行各个爬虫
    spiders = ["coffee_shrub", "sweet_marias", "genuine_origin"]
    success_count = 0
    
    for spider in spiders:
        if run_scraper(spider):
            success_count += 1
    
    # 只要有一个爬虫成功，就尝试合并数据
    if success_count > 0:
        if run_merger():
            # 生成报表并发送邮件
            generate_and_send_report(RECIPIENTS)
        else:
            logger.error("数据合并失败，无法生成报表")
    else:
        logger.error("所有爬虫都失败，无法继续后续流程")
    
    logger.info("完整流程结束")

def setup_schedule():
    """设置定时任务"""
    # 每天凌晨2点运行
    schedule.every().day.at("02:00").do(run_full_process)
    
    # 每周一早上9点运行
    schedule.every().monday.at("09:00").do(run_full_process)
    
    logger.info("定时任务已设置")
    logger.info("- 每天凌晨2:00运行")
    logger.info("- 每周一上午9:00运行")

if __name__ == "__main__":
    setup_environment()
    
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # 立即运行一次
        logger.info("收到立即运行参数，开始执行...")
        run_full_process()
    else:
        # 设置定时任务
        setup_schedule()
        
        logger.info("开始定时任务调度器，按Ctrl+C退出")
        try:
            # 保持脚本运行，等待定时任务执行
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次是否有定时任务需要运行
        except KeyboardInterrupt:
            logger.info("接收到退出信号，退出调度器") 