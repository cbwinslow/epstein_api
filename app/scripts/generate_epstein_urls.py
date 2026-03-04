#!/usr/bin/env python3
"""
Script to generate DOJ Epstein file URLs for bulk download.
"""

BASE_URL = "https://www.justice.gov/epstein/files"

def generate_dataset_urls(dataset_num, num_files=100):
    """Generate URLs for a specific dataset."""
    urls = []
    for i in range(1, num_files + 1):
        file_num = str(i).zfill(8)
        url = f"{BASE_URL}/DataSet%20{dataset_num}/EFTA{file_num}.pdf"
        urls.append(url)
    return urls

if __name__ == "__main__":
    # Generate first 10 URLs from Data Set 1
    urls = generate_dataset_urls(1, 10)
    for url in urls:
        print(url)
