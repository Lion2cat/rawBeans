@echo off
echo "========================================="
echo "Starting coffee data collection and merge"
echo "========================================="

REM Set current directory as the project root
cd /d %~dp0

REM Run each spider
echo.
echo "Running Coffee Shrub spider..."
python run_coffee_shrub_spider.py
echo "Coffee Shrub spider completed"

echo.
echo "Running Sweet Maria's spider..."
python run_sweet_marias_spider.py
echo "Sweet Maria's spider completed"

echo.
echo "Running Genuine Origin spider..."
python run_genuine_origin_spider.py
echo "Genuine Origin spider completed"

REM Merge the results
echo.
echo "Merging coffee data from all sources..."
python merge_coffee_results.py

echo.
echo "Process completed! Check the 'results' directory for the merged data."
echo "=========================================" 