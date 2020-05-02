# https://github.com/tnware/product-checker
# by Tyler Woods
# coded for Bird Bot and friends
# https://tylermade.net
import requests
import time
import json
from datetime import datetime
import urllib.parse as urlparse
from urllib.parse import parse_qs
from threading import Thread
from random import randint
from selenium import webdriver
from chromedriver_py import binary_path as driver_path

stockdict = {}  # Map of URLs to the last time they were seen in stock
sku_dict = {}
bestbuylist = []
targetlist = []
walmartlist = []
bhlist = []
bbdict = {}
amazonlist = []
gamestoplist = []

# ITEM_FOUND_TIMEOUT = 60 * 60 * 3  # 3 hours
ITEM_FOUND_TIMEOUT = 10
THREAD_JITTER = 90
CHECK_INTERVAL = 30  # Check once every [30-90s]


def post_url(key, webhook_url, slack_data):
    requests.post(
        webhook_url, data=json.dumps(slack_data),
        headers={'Content-Type': 'application/json'})

def return_data(path):
    with open(path, "r") as file:
        data = json.load(file)
    file.close()
    return data


# Only declare the webhook and product lists after the menu has been passed so that changes made from menu selections are up to date
webhook_dict = return_data("./data/webhooks.json")
urldict = return_data("./data/products.json")


def Amazon(url, hook):
    webhook_url = webhook_dict[hook]
    now = datetime.now()
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('log-level=3')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument(
        '--user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"')
    options.add_argument("headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(executable_path='/usr/lib/chromium-browser/chromedriver', options=options)
    driver.get(url)

    html = driver.page_source
    if "To discuss automated access to Amazon data please contact api-services-support@amazon.com." in html:
        print("Amazons Bot Protection is preventing this call.")
    else:
        status_raw = driver.find_element_by_xpath("//div[@id='olpOfferList']")
        status_text = status_raw.text
        title_raw = driver.find_element_by_xpath("//h1[@class='a-size-large a-spacing-none']")
        title = title_raw.text

        try:
            if "Currently, there are no sellers that can deliver this item to your location." not in status_text:
                # print("[" + current_time + "] " + "In Stock: (Amazon.com) " + title + " - " + url)
                slack_data = {'value1': "Amazon", 'value2': url, 'value3': title}
                post_url(url, webhook_url, slack_data)
                return True
            else:
                # print("[" + current_time + "] " + "Sold Out: (Amazon.com) " + title)
                stockdict.update({url: None})
                return False
        finally:
            driver.quit()


def Gamestop(url, hook):
    webhook_url = webhook_dict[hook]
    now = datetime.now()
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('log-level=3')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument(
        '--user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"')
    options.add_argument("headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(executable_path='/usr/lib/chromium-browser/chromedriver', chrome_options=options)
    driver.get(url)

    status_raw = driver.find_element_by_xpath("//div[@class='add-to-cart-buttons']")
    status_text = status_raw.text
    title_raw = driver.find_element_by_xpath("//h1[@class='product-name h2']")
    title = title_raw.text

    try:
        if "ADD TO CART" in status_text:
            slack_data = {'value1': "Gamestop", 'value2': url, 'value3': title}
            post_url(url, webhook_url, slack_data)
            return True
        return False
    finally:
        driver.quit()


def Target(url, hook):
    webhook_url = webhook_dict[hook]
    now = datetime.now()
    page = requests.get(url)
    al = page.text
    title = al[al.find('"twitter":{"title":') + 20 : al.find('","card')]
    if "Temporarily out of stock" not in page.text:
        # print("[" + current_time + "] " + "In Stock: (Target.com) " + title + " - " + url)
        slack_data = {'value1': "Target", 'value2': url, 'value3': title}
        post_url(url, webhook_url, slack_data)
        return True
    return False


def BestBuy(sku, hook):
    webhook_url = webhook_dict[hook]
    now = datetime.now()
    url = "https://www.bestbuy.com/api/tcfb/model.json?paths=%5B%5B%22shop%22%2C%22scds%22%2C%22v2%22%2C%22page%22%2C%22tenants%22%2C%22bbypres%22%2C%22pages%22%2C%22globalnavigationv5sv%22%2C%22header%22%5D%2C%5B%22shop%22%2C%22buttonstate%22%2C%22v5%22%2C%22item%22%2C%22skus%22%2C" + sku + "%2C%22conditions%22%2C%22NONE%22%2C%22destinationZipCode%22%2C%22%2520%22%2C%22storeId%22%2C%22%2520%22%2C%22context%22%2C%22cyp%22%2C%22addAll%22%2C%22false%22%5D%5D&method=get"
    headers2 = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "cache-control": "max-age=0",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.69 Safari/537.36"
    }
    page = requests.get(url, headers=headers2)
    link = "https://www.bestbuy.com/site/" + sku + ".p?skuId=" + sku
    al = page.text
    search_string = '"skuId":"' + sku + '","buttonState":"'
    stock_status = al[al.find(search_string) + 33: al.find('","displayText"')]
    product_name = sku_dict.get(sku)
    if stock_status == "SOLD_OUT":
        # print("[" + current_time + "] " + "Sold Out: (BestBuy.com) " + product_name)
        stockdict.update({sku: None})
    elif stock_status == "CHECK_STORES":
        # print(product_name + " sold out @ BestBuy (check stores status)")
        stockdict.update({sku: None})
    else:
        if stock_status == "ADD_TO_CART":
            # print("[" + current_time + "] " + "In Stock: (BestBuy.com) " + product_name + " - " + link)
            slack_data = {'value1': "Best Buy", 'value2': link, 'value3': product_name}
            post_url(link, webhook_url, slack_data)
            return True
    return False


def Walmart(url, hook):
    webhook_url = webhook_dict[hook]
    now = datetime.now()
    page = requests.get(url)
    if page.status_code == 200:
        if "Add to cart" in page.text:
            # print("[" + current_time + "] " + "In Stock: (Walmart.com) " + url)
            slack_data = {'value1': "Walmart", 'value2': url, 'value3': 'Some item'}
            post_url(url, webhook_url, slack_data)
            return True
        return False


def BH(url, hook):
    webhook_url = webhook_dict[hook]
    page = requests.get(url)
    if page.status_code == 200:
        if "Add to Cart" in page.text:
            slack_data = {'value1': "B&H", 'value2': url, 'value3': "Some item"}
            post_url(url, webhook_url, slack_data)
            return True
        return False


# Classify all the URLs by site

for url in urldict:
    hook = urldict[url]  # get the hook for the url so it can be passed in to the per-site lists being generated below

    # Amazon URL Detection
    if "amazon.com" in url:
        if "offer-listing" in url:
            amazonlist.append(url)
            # print("Amazon detected using Webhook destination " + hook)
        else:
            print("Invalid Amazon link detected. Please use the Offer Listing page.")

    # Target URL Detection
    elif "gamestop.com" in url:
        gamestoplist.append(url)

    # BestBuy URL Detection
    elif "bestbuy.com" in url:
        parsed = urlparse.urlparse(url)
        sku = parse_qs(parsed.query)['skuId']
        sku = sku[0]
        bestbuylist.append(sku)
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.69 Safari/537.36"
        }
        page = requests.get(url, headers=headers)
        al = page.text
        title = al[al.find('<title >') + 8: al.find(' - Best Buy</title>')]
        sku_dict.update({sku: title})
        bbdict.update({sku: hook})

    # Target URL Detection
    elif "target.com" in url:
        targetlist.append(url)

    # Walmart URL Detection
    elif "walmart.com" in url:
        walmartlist.append(url)

    # B&H Photo URL Detection
    elif "bhphotovideo.com" in url:
        bhlist.append(url)

# set all URLs to be "out of stock" to begin
for url in urldict:
    stockdict.update({url: None})
# set all SKUs to be "out of stock" to begin
for sku in sku_dict:
    stockdict.update({sku: None})


# DECLARE SITE FUNCTIONS

def amzfunc(url):
    while True:
        hook = urldict[url]
        try:
            if Amazon(url, hook):
                 time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            print("Some error ocurred parsing Amazon: ", e)


def gamestopfunc(url):
    while True:
        hook = urldict[url]
        try:
            if Gamestop(url, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            print("Some error ocurred parsing Gamestop: ", e)


def targetfunc(url):
    while True:
        hook = urldict[url]
        try:
            if Target(url, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            print("Some error ocurred parsing Target: ", e)


def bhfunc(url):
    while True:
        hook = urldict[url]
        try:
            if BH(url, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            print("Some error ocurred parsing BH Photo: ", e)
        time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))


def bestbuyfunc(sku):
    while True:
        hook = bbdict[sku]
        try:
            if BestBuy(sku, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            print("Some error ocurred parsing Best Buy: ", e)


def walmartfunc(url):
    while True:
        hook = urldict[url]
        try:
            if Walmart(url, hook):
                time.sleep(ITEM_FOUND_TIMEOUT)
            else:
                time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))
        except Exception as e:
            print("Some error ocurred parsing WalMart: ", e)
        time.sleep(CHECK_INTERVAL + randint(0, THREAD_JITTER))


# MAIN EXECUTION

for url in amazonlist:
    t = Thread(target=amzfunc, args=(url,))
    t.start()
    time.sleep(0.5)

for url in gamestoplist:
    t = Thread(target=gamestopfunc, args=(url,))
    t.start()
    time.sleep(4)

for url in targetlist:
    t = Thread(target=targetfunc, args=(url,))
    t.start()
    time.sleep(0.5)

for url in bhlist:
    t = Thread(target=bhfunc, args=(url,))
    t.start()
    time.sleep(0.5)

for sku in bestbuylist:
    t = Thread(target=bestbuyfunc, args=(sku,))
    t.start()
    time.sleep(0.5)

for url in walmartlist:
    t = Thread(target=walmartfunc, args=(url,))
    t.start()
    time.sleep(0.5)

print("Finished Starting Product Tracker!")
