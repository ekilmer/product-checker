from bs4 import BeautifulSoup, SoupStrainer
from typing import Any
from datetime import datetime
import requests
import sys

def parse_newegg_page(url: str):
    page = requests.get(url=url, headers=HEADERS)
    if not page.text:
        log(f'Response body is empty for Newegg product lookup {url}')
        return

    buy_section = BeautifulSoup(page.text, 'lxml', parse_only=SoupStrainer(id='ProductBuy'))

    product_title = BeautifulSoup(page.text, 'lxml', parse_only=SoupStrainer(class_='product-title'))
    if not product_title:
        log("Newegg could not parse product name")
        product_title = "NEWEGG ITEM"
    else:
        product_title = product_title.text
    
    if buy_section:
        if 'Add to cart' in buy_section.text:
            log(f"IN STOCK: {product_title}")
        else:
            log(f"NOT IN STOCK: {product_title}")
    else:
        log(f'No Newegg buy section found for URL {url}')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        log("Need two arguments: product_string url")
    parse_newegg_page(sys.argv[1])
