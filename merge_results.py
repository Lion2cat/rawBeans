import os
import json
import glob
import logging
from pathlib import Path
from datetime import datetime

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("merge_results.log")
        ]
    )
    return logging.getLogger(__name__)

def find_latest_files(directory, pattern):
    """Find the latest files matching the pattern in the directory"""
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return []
    
    # Sort files by modification time (newest first)
    return sorted(files, key=os.path.getmtime, reverse=True)

def load_json_file(file_path):
    """Load JSON data from a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def deduplicate_products(products):
    """Deduplicate products based on name and supplier"""
    # Use a dictionary to track unique products
    unique_products = {}
    
    for product in products:
        # Create a key using name and supplier
        if 'name' not in product or 'supplier' not in product:
            continue
            
        key = f"{product['name']}_{product['supplier']}".lower()
        
        # Only keep the first occurrence (or the one with more information)
        if key not in unique_products:
            unique_products[key] = product
    
    return list(unique_products.values())

def merge_results():
    """Merge and deduplicate results from different spiders"""
    logger = setup_logging()
    logger.info("Starting to merge results")
    
    # Get the project root directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = Path(project_dir) / 'results'
    
    if not results_dir.exists():
        logger.error(f"Results directory not found: {results_dir}")
        return
    
    # Find the latest results from each spider
    coffee_shrub_files = find_latest_files(results_dir, "coffee_shrub_*.json")
    sweet_marias_files = find_latest_files(results_dir, "sweet_marias_*.json")
    
    if not coffee_shrub_files:
        logger.warning("No Coffee Shrub results found")
    else:
        logger.info(f"Found Coffee Shrub results: {coffee_shrub_files[0]}")
        
    if not sweet_marias_files:
        logger.warning("No Sweet Maria's results found")
    else:
        logger.info(f"Found Sweet Maria's results: {sweet_marias_files[0]}")
    
    if not coffee_shrub_files and not sweet_marias_files:
        logger.error("No result files found to merge")
        return
    
    # Load the data from all files
    all_products = []
    
    for file_path in coffee_shrub_files[:1] + sweet_marias_files[:1]:  # Take only the latest file from each
        try:
            products = load_json_file(file_path)
            logger.info(f"Loaded {len(products)} products from {file_path}")
            all_products.extend(products)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
    
    # Deduplicate products
    unique_products = deduplicate_products(all_products)
    logger.info(f"After deduplication: {len(unique_products)} unique products")
    
    # Save merged results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = results_dir / f"merged_coffee_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_products, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Merged results saved to {output_file}")
    return output_file

if __name__ == "__main__":
    merge_results() 