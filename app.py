# https://github.com/tnware/product-checker
# by Tyler Woods
# coded for Bird Bot and friends
# https://tylermade.net
from typing import Any

import requests
import time
import json
from datetime import datetime
import urllib.parse as urlparse
from urllib.parse import parse_qs
from threading import Thread, Semaphore
from random import randint
from selenium import webdriver
from chromedriver_py import binary_path as driver_path
from sys import platform
from os import cpu_count

from selenium.webdriver.chrome.webdriver import WebDriver

sku_dict = {}
bestbuylist = []
targetlist = []
walmartlist = []
bhlist = []
bbdict = {}
amazonlist = []
gamestoplist = []

chromedriver_path = driver_path
concurrent_chromedriver_instances = cpu_count()
if platform == "linux":
    chromedriver_path = '/usr/lib/chromium-browser/chromedriver'
    concurrent_chromedriver_instances = 3

# Limit the number of chromedriver instances to not starve the Pi of resources
chromedriver_semphabore = Semaphore(concurrent_chromedriver_instances)

ITEM_FOUND_TIMEOUT = 60 * 60 * 6  # 3 hours
THREAD_JITTER = 15
CHECK_INTERVAL = 15  # Check once every [15-30s]


def log(msg: Any, *msgv):
    print("[" + datetime.now().strftime("%m/%d %H:%M:%S") + "]", msg, msgv)


def return_data(path):
    with open(path, "r") as file:
        data = json.load(file)
    file.close()
    return data


webhook_dict = return_data("./data/webhooks.json")
urldict = return_data("./data/products.json")


def post_webhook(webhook_url: str, slack_data: dict):
    requests.post(
        webhook_url, data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'})


def get_driver() -> WebDriver:
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('log-level=3')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument(
        '--user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 '
        'Safari/537.36"')
    options.add_argument("headless")
    if platform == "linux":
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)
    driver.set_page_load_timeout(15)
    return driver


def Amazon(url, hook):
    webhook_url = webhook_dict[hook]

    chromedriver_semphabore.acquire()
    driver = get_driver()
    driver.get(url)
    chromedriver_semphabore.release()

    html = driver.page_source
    if "To discuss automated access to Amazon data please contact api-services-support@amazon.com." in html:
        log("Amazons Bot Protection is preventing this call.")
    else:
        status_raw = driver.find_element_by_xpath("//div[@id='olpOfferList']")
        status_text = status_raw.text
        title_raw = driver.find_element_by_xpath("//h1[@class='a-size-large a-spacing-none']")
        title = title_raw.text
        driver.quit()
        if "Currently, there are no sellers that can deliver this item to your location." not in status_text:
            slack_data = {'value1': "Amazon", 'value2': url, 'value3': title}
            post_webhook(webhook_url, slack_data)
            return True
        return False


def Gamestop(url, hook):
    webhook_url = webhook_dict[hook]

    chromedriver_semphabore.acquire()
    driver = get_driver()
    driver.get(url)
    chromedriver_semphabore.release()

    status_raw = driver.find_element_by_xpath("//div[@class='add-to-cart-buttons']")
    status_text = status_raw.text
    title_raw = driver.find_element_by_xpath("//h1[@class='product-name h2']")
    title = title_raw.text
    driver.quit()
    if "ADD TO CART" in status_text:
        slack_data = {'value1': "Gamestop", 'value2': url, 'value3': title}
        post_webhook(webhook_url, slack_data)
        return True
    return False


def BestBuy(sku, hook):
    webhook_url = webhook_dict[hook]
    url = "https://www.bestbuy.com/api/tcfb/model.json?paths=%5B%5B%22shop%22%2C%22scds%22%2C%22v2%22%2C%22page%22%2C" \
          "%22tenants%22%2C%22bbypres%22%2C%22pages%22%2C%22globalnavigationv5sv%22%2C%22header%22%5D%2C%5B%22shop%22" \
          "%2C%22buttonstate%22%2C%22v5%22%2C%22item%22%2C%22skus%22%2C" + sku + \
          "%2C%22conditions%22%2C%22NONE%22%2C%22destinationZipCode%22%2C%22%2520%22%2C%22storeId%22%2C%22%2520%22%2C" \
          "%22context%22%2C%22cyp%22%2C%22addAll%22%2C%22false%22%5D%5D&method=get "
    headers2 = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "cache-control": "max-age=0",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/81.0.4044.69 Safari/537.36 "
    }
    page = requests.get(url, headers=headers2)
    link = "https://www.bestbuy.com/site/" + sku + ".p?skuId=" + sku
    al = page.text
    search_string = '"skuId":"' + sku + '","buttonState":"'
    stock_status = al[al.find(search_string) + 33: al.find('","displayText"')]
    product_name = sku_dict.get(sku)
    if stock_status == "ADD_TO_CART":
        slack_data = {'value1': "Best Buy", 'value2': link, 'value3': product_name}
        post_webhook(webhook_url, slack_data)
        return True
    return False


# A CheckerFunc take a page and returns the item title if the item is in stock
def target_checker(resp: requests.Response) -> str:
    page = resp.text
    status = page[page.find('"availability_status":"') + 23 : page.find('","multichannel_options"')]
    if status == "IN_STOCK":
        title = page[page.find('"twitter":{"title":') + 20: page.find('","card')]
        return title
    return ""


def walmart_checker(resp: requests.Response) -> str:
    if "Add to cart" in resp.text:
        return "Something"
    return ""


def bh_checker(resp: requests.Response) -> str:
    if "Add to Cart" in resp.text:
        return "An item"
    return ""


# ThreadFunc takes a URL and a CheckerFunc
def ThreadFunc(url: str, store: str, checker):
    hook = urldict[url]
    webhook_url = webhook_dict[hook]
    while True:
        try:
            page = requests.get(url)
            if page.status_code == 200:
                title = checker(page)
                if title != "":
                    slack_data = {'value1': store, 'value2': url, 'value3': title}
                    post_webhook(webhook_url, slack_data)
                    time.sleep(ITEM_FOUND_TIMEOUT)
                else:
                    time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
            else:
                log(f'Non 200 status code: {page.status_code} for {url} due to {page.content}')
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            log("Some error ocurred: ", e)
            time.sleep(CHECK_INTERVAL)


# GetFuncFromURL takes a URL and return the corresponding checkerfunc
def GetFuncFromURL(url: str):
    if "target.com" in url:
        return target_checker, "Target"
    elif "walmart.com" in url:
        return walmart_checker, "Walmart"
    elif "bhphotovideo.com" in url:
        return bh_checker, "B&H"
    return None, None


def amzfunc(url):
    while True:
        hook = urldict[url]
        try:
            if Amazon(url, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            log("Some error occurred parsing Amazon: ", e)
            time.sleep(CHECK_INTERVAL)


def gamestopfunc(url):
    while True:
        hook = urldict[url]
        try:
            if Gamestop(url, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            log("Some error ocurred parsing Gamestop: ", e)
            time.sleep(CHECK_INTERVAL)


def bestbuyfunc(sku):
    while True:
        hook = bbdict[sku]
        try:
            if BestBuy(sku, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            log("Some error ocurred parsing Best Buy: ", e)
            time.sleep(CHECK_INTERVAL)


def parse_urls():
    for url in urldict:
        hook = urldict[url]  # get the hook for the url so it can be passed in to the per-site lists being generated below

        # Amazon URL Detection
        if "amazon.com" in url:
            if "offer-listing" in url:
                amazonlist.append(url)
            else:
                print("Invalid Amazon link detected. Please use the Offer Listing page.")

        # Gamestop URL Detection
        elif "gamestop.com" in url:
            gamestoplist.append(url)

        # BestBuy URL Detection
        elif "bestbuy.com" in url:
            parsed = urlparse.urlparse(url)
            sku = parse_qs(parsed.query)['skuId']
            sku = sku[0]
            bestbuylist.append(sku)
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
                          "application/signed-exchange;v=b3;q=0.9",
                "accept-encoding": "gzip, deflate, br",
                "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "cache-control": "max-age=0",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/81.0.4044.69 Safari/537.36 "
            }
            page = requests.get(url, headers=headers)
            al = page.text
            title = al[al.find('<title >') + 8: al.find(' - Best Buy</title>')]
            sku_dict.update({sku: title})
            bbdict.update({sku: hook})


def main():
    parse_urls()
    log("Starting Product Tracker!")
    # Add generic support for more websites
    for url in urldict:
        func, store = GetFuncFromURL(url)
        if func is not None:
            thread = Thread(target=ThreadFunc, args=(url, store, func))
            thread.start()
            time.sleep(0.5)
    for amzurl in amazonlist:
        t = Thread(target=amzfunc, args=(amzurl,))
        t.start()
        time.sleep(0.5)

    for gsurl in gamestoplist:
        t = Thread(target=gamestopfunc, args=(gsurl,))
        t.start()
        time.sleep(1)

    for sku in bestbuylist:
        t = Thread(target=bestbuyfunc, args=(sku,))
        t.start()
        time.sleep(0.5)
    log("Finished Starting Product Tracker!")


main()
