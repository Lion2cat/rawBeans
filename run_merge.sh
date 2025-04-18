#!/bin/bash

echo "========================================="
echo "Starting coffee data collection and merge"
echo "========================================="

# Ensure we're in the project root directory
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR"

# Run each spider
echo
echo "Running Coffee Shrub spider..."
python run_coffee_shrub_spider.py
echo "Coffee Shrub spider completed"

echo
echo "Running Sweet Maria's spider..."
python run_sweet_marias_spider.py
echo "Sweet Maria's spider completed"

echo
echo "Running Genuine Origin spider..."
python run_genuine_origin_spider.py
echo "Genuine Origin spider completed"

# Merge the results
echo
echo "Merging coffee data from all sources..."
python merge_coffee_results.py

echo
echo "Process completed! Check the 'results' directory for the merged data."
echo "=========================================" 