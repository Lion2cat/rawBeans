import os
import sys
import json
import glob
import logging
from pathlib import Path
from datetime import datetime

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def find_latest_files(results_dir, patterns):
    """Find the latest JSON files for each scraper"""
    logger = logging.getLogger(__name__)
    latest_files = {}
    
    for pattern in patterns:
        # Get all files matching the pattern
        pattern_path = os.path.join(results_dir, pattern)
        matching_files = glob.glob(pattern_path)
        
        if not matching_files:
            logger.warning(f"No files found matching pattern: {pattern}")
            continue
            
        # Sort files by modification time (newest first)
        matching_files.sort(key=os.path.getmtime, reverse=True)
        latest_file = matching_files[0]
        
        # Extract supplier name from filename pattern
        supplier = pattern.split('_')[0]
        latest_files[supplier] = latest_file
        logger.info(f"Latest {supplier} file: {os.path.basename(latest_file)}")
    
    return latest_files

def load_json_data(file_path):
    """Load JSON data from a file"""
    logger = logging.getLogger(__name__)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data)} products from {os.path.basename(file_path)}")
            return data
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return []

def is_duplicate(product, merged_products):
    """Check if a product is a duplicate in the merged list"""
    # Check for duplicates based on name, origin and supplier
    for existing in merged_products:
        # If same supplier and product name, it's a duplicate
        if (existing.get('supplier') == product.get('supplier') and 
            existing.get('name') == product.get('name')):
            return True
            
        # If same name and origin across suppliers, consider it a duplicate
        if (existing.get('name') == product.get('name') and 
            existing.get('origin') == product.get('origin') and
            existing.get('origin') is not None):
            return True
    
    return False

def merge_coffee_data():
    """Merge coffee data from multiple scrapers"""
    logger = setup_logging()
    logger.info("Starting coffee data merger")
    
    # Get project root directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ensure we're in the project root
    os.chdir(project_dir)
    
    # Define the results directory
    results_dir = os.path.join(project_dir, 'results')
    if not os.path.exists(results_dir):
        logger.warning(f"Results directory not found at {results_dir}")
        logger.info("Creating results directory")
        os.makedirs(results_dir)
    
    # Define file patterns to search for
    file_patterns = [
        'sweet_marias_*.json',
        'coffee_shrub_*.json',
        'genuine_origin_*.json'
    ]
    
    # Find the latest files for each scraper
    latest_files = find_latest_files(results_dir, file_patterns)
    
    if not latest_files:
        logger.error("No scraper output files found. Run scrapers first.")
        return
    
    # Merge the data
    merged_products = []
    total_products = 0
    duplicates_removed = 0
    
    for supplier, file_path in latest_files.items():
        products = load_json_data(file_path)
        total_products += len(products)
        
        for product in products:
            if not is_duplicate(product, merged_products):
                merged_products.append(product)
            else:
                duplicates_removed += 1
    
    logger.info(f"Total products found: {total_products}")
    logger.info(f"Duplicates removed: {duplicates_removed}")
    logger.info(f"Merged products: {len(merged_products)}")
    
    # Sort the merged data by origin and supplier
    merged_products.sort(key=lambda x: (x.get('origin', ''), x.get('supplier', '')))
    
    # Save the merged data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(results_dir, f'merged_coffee_data_{timestamp}.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_products, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Merged data saved to {output_file}")
    return output_file

if __name__ == '__main__':
    merge_coffee_data() 