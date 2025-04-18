# Coffee Bean Data Collection & Aggregation

This project collects coffee bean data from various suppliers' websites using web scraping techniques and merges the results into a single dataset. It is designed to handle anti-scraping protections like Cloudflare and dynamic content loading.

## Features

- Automated scraping of multiple coffee bean supplier websites:
  - Sweet Maria's
  - Coffee Shrub
  - Genuine Origin
- Cloudflare protection bypass using undetected-chromedriver
- Selenium-based scraping with human-like interaction patterns
- Backup HTML content parsing with BeautifulSoup
- Deduplication and merging of data from multiple sources
- Standardized data format with price, origin, and supplier information

## Requirements

- Python 3.8+
- Chrome browser installed
- Python packages (see requirements.txt):
  - selenium
  - undetected-chromedriver
  - beautifulsoup4
  - scrapy (for optional Scrapy-based spiders)

## Installation

1. Clone this repository
2. Install dependencies:
   
   ```
   pip install -r requirements.txt
   ```

3. Ensure Chrome browser is installed on your system

## Usage

### Running Individual Scrapers

To run individual scrapers:

```
python run_sweet_marias_spider.py
python run_coffee_shrub_spider.py
python run_genuine_origin_spider.py
```

Each scraper will:
- Create a results directory if it doesn't exist
- Save data as JSON in the results directory
- Save debug HTML files in the results directory

### Merging Results

To merge results from all scrapers:

```
python merge_coffee_results.py
```

The merge script will:
- Find the latest data files from each source
- Merge and deduplicate the products
- Save the combined data to a timestamped JSON file

### Running the Full Pipeline

For Windows:
```
run_merge_script.bat
```

For Mac/Linux:
```
chmod +x run_merge.sh
./run_merge.sh
```

## Data Format

The collected data follows this format:

```json
{
  "name": "Ethiopia Guji Benti Nenka",
  "supplier": "Sweet Maria's",
  "price": 8.55,
  "currency": "USD",
  "origin": "Ethiopia",
  "url": "https://www.sweetmarias.com/ethiopia-guji-benti-nenka-8131.html",
  "updated_at": "2025-04-18"
}
```

## Troubleshooting

- **ChromeDriver version issues**: If you encounter errors related to Chrome version, modify the `version_main` parameter in the `setup_driver()` function to match your Chrome version.
  
- **Cloudflare Detection**: If the scrapers are being blocked by Cloudflare, try:
  - Increasing wait times
  - Adding more human-like interaction patterns
  - Running in non-headless mode for debugging

- **Empty Results**: In some cases, websites may change their structure. The scrapers are designed to try multiple CSS selectors, but you may need to update them if the site structure changes significantly.

## License

This project is for educational purposes only. Always respect websites' terms of service and robots.txt rules.