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
import webhook_settings
import product_settings
from threading import Thread
from selenium import webdriver
from chromedriver_py import binary_path as driver_path
stockdict = {} # Map of URLs to the last time they were seen in stock
sku_dict = {}
bestbuylist = []
targetlist = []
walmartlist = []
bhlist = []
bbdict = {}
amazonlist = []
gamestoplist = []

URL_CACHE_TIMEOUT = 60 * 60 * 6  # 6 hours


def post_url(key, webhook_url, slack_data):
    val = stockdict.get(key, None)
    if val is None or time.time() - val > URL_CACHE_TIMEOUT:
        response = requests.post(
            webhook_url, data=json.dumps(slack_data),
            headers={'Content-Type': 'application/json'})
        stockdict.update({key: time.time()})


#Function for start-up menu

def menu():
    webhook_dict = return_data("./data/webhooks.json")
    urldict = return_data("./data/products.json")
    print("Select an Option: \n 1: Edit Webhooks \n 2: Edit Product URLs \n 3: Run the product tracker \n")
    val = input("Enter # (1-3)")
    if val == "1":
        webhook_settings.main()
        menu()
    elif val == "2":
        product_settings.main()
        menu()
    elif val == "3":
        print("\n Starting Product Tracker! \n")
    else:
        menu()

def return_data(path):
    with open(path,"r") as file:
        data = json.load(file)
    file.close()
    return data

#Prompt the user at startup
menu()

#Only declare the webhook and product lists after the menu has been passed so that changes made from menu selections are up to date
webhook_dict = return_data("./data/webhooks.json")
urldict = return_data("./data/products.json")

#Declare classes for the webpage scraping functionality

class Amazon:

    def __init__(self, url, hook):
        self.url = url
        self.hook = hook
        webhook_url = webhook_dict[hook]
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument('log-level=3')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"')
        options.add_argument("headless")
        driver = webdriver.Chrome(executable_path=driver_path, options=options)
        driver.get(url)

        html = driver.page_source
        if "To discuss automated access to Amazon data please contact api-services-support@amazon.com." in html:
            print("Amazons Bot Protection is preventing this call.")
        else:
            status_raw = driver.find_element_by_xpath("//div[@id='olpOfferList']")
            status_text = status_raw.text
            title_raw = driver.find_element_by_xpath("//h1[@class='a-size-large a-spacing-none']")
            title_text = title_raw.text
            title = title_text

            if "Currently, there are no sellers that can deliver this item to your location." not in status_text:
                # print("[" + current_time + "] " + "In Stock: (Amazon.com) " + title + " - " + url)
                slack_data = {'value1': "Amazon", 'value2': url}
                if stockdict.get(url) == None:
                    response = requests.post(
                    webhook_url, data=json.dumps(slack_data),
                    headers={'Content-Type': 'application/json'})
                stockdict.update({url: 'True'})
            else:
                # print("[" + current_time + "] " + "Sold Out: (Amazon.com) " + title)
                stockdict.update({url: None})
        driver.quit()

class Gamestop:

    def __init__(self, url, hook):
        self.url = url
        self.hook = hook
        webhook_url = webhook_dict[hook]
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument('log-level=3')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"')
        options.add_argument("headless")
        driver = webdriver.Chrome(executable_path=driver_path, chrome_options=options)
        driver.get(url)

        html = driver.page_source

        status_raw = driver.find_element_by_xpath("//div[@class='add-to-cart-buttons']")
        status_text = status_raw.text
        title_raw = driver.find_element_by_xpath("//h1[@class='product-name h2']")
        title_text = title_raw.text
        title = title_text

        if "ADD TO CART" in status_text:
            # print("[" + current_time + "] " + "In Stock: (Gamestop.com) " + title + " - " + url)
            slack_data = {'value1': "Gamestop", 'value2': url}
            if stockdict.get(url) == None:
                response = requests.post(
                webhook_url, data=json.dumps(slack_data),
                headers={'Content-Type': 'application/json'})
            stockdict.update({url: 'True'})
        else:
            # print("[" + current_time + "] " + "Sold Out: (Gamestop.com) " + title)
            stockdict.update({url: None})
        driver.quit()

class Target:

    def __init__(self, url, hook):
        self.url = url
        self.hook = hook
        webhook_url = webhook_dict[hook]
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        page = requests.get(url)
        al = page.text
        title = al[al.find('"twitter":{"title":') + 20 : al.find('","card')]
        #print(title)
        if "Temporarily out of stock" in page.text:
            # print("[" + current_time + "] " + "Sold Out: (Target.com) " + title)
            stockdict.update({url: None})
        else:
            # print("[" + current_time + "] " + "In Stock: (Target.com) " + title + " - " + url)
            slack_data = {'value1': "Target", 'value2': url}
            post_url(url, webhook_url, slack_data)
        #print(stockdict)

class BestBuy:

    def __init__(self, sku, hook):
        self.sku = sku
        self.hook = hook
        webhook_url = webhook_dict[hook]
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
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
        stock_status = al[al.find(search_string) + 33 : al.find('","displayText"')]
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
                slack_data = {'value1': "Best Buy", 'value2': link}
                post_url(link, webhook_url, slack_data)

class Walmart:

    def __init__(self, url, hook):
        self.url = url
        self.hook = hook
        webhook_url = webhook_dict[hook]
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        page = requests.get(url)
        if page.status_code == 200:
            if "Add to cart" in page.text:
                # print("[" + current_time + "] " + "In Stock: (Walmart.com) " + url)
                slack_data = {'value1': "Walmart", 'value2': url}
                if stockdict.get(url) == None:
                    try:
                        response = requests.post(
                        webhook_url, data=json.dumps(slack_data),
                        headers={'Content-Type': 'application/json'})
                    except:
                        print("Webhook sending failed. Invalid URL configured.")
                stockdict.update({url: 'True'})
            else:
                # print("[" + current_time + "] " + "Sold Out: (Walmart.com) " + url)
                stockdict.update({url: None})

class BH:

    def __init__(self, url, hook):
        self.url = url
        self.hook = hook
        webhook_url = webhook_dict[hook]
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        page = requests.get(url)
        if page.status_code == 200:
            if "Add to Cart" in page.text:
                # print("[" + current_time + "] " + "In Stock: (bhphotovideo.com) " + url)
                slack_data = {'value1': "B&H", 'value2': url}
                post_url(url, webhook_url, slack_data)
            else:
                # print("[" + current_time + "] " + "Sold Out: (bhphotovideo.com) " + url)
                stockdict.update({url: None})

#Classify all the URLs by site

for url in urldict:
    hook = urldict[url] #get the hook for the url so it can be passed in to the per-site lists being generated below

    #Amazon URL Detection
    if "amazon.com" in url:
        if "offer-listing" in url:
            amazonlist.append(url)
            # print("Amazon detected using Webhook destination " + hook)
        else:
            print("Invalid Amazon link detected. Please use the Offer Listing page.")

   #Target URL Detection
    elif "gamestop.com" in url:
        gamestoplist.append(url)
        # print("Gamestop URL detected using Webhook destination " + hook)

    #BestBuy URL Detection
    elif "bestbuy.com" in url:
        # print("BestBuy URL detected using Webhook destination " + hook)
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
        title = al[al.find('<title >') + 8 : al.find(' - Best Buy</title>')]
        sku_dict.update({sku: title})
        bbdict.update({sku: hook})

    #Target URL Detection
    elif "target.com" in url:
        targetlist.append(url)
        # print("Target URL detected using Webhook destination " + hook)

    #Walmart URL Detection
    elif "walmart.com" in url:
        walmartlist.append(url)
        # print("Walmart URL detected using Webhook destination " + hook)

    #B&H Photo URL Detection
    elif "bhphotovideo.com" in url:
        bhlist.append(url)
        # print("B&H URL detected using Webhook destination " + hook)

#set all URLs to be "out of stock" to begin
for url in urldict:
    stockdict.update({url: None})
#set all SKUs to be "out of stock" to begin
for sku in sku_dict:
    stockdict.update({sku: None})

#DECLARE SITE FUNCTIONS

def amzfunc(url):
    while True:
        hook = urldict[url]
        try:
            Amazon(url, hook)
        except Exception as e:
            print("Some error ocurred parsing Amazon: ", e)
        time.sleep(10)

def gamestopfunc(url):
    while True:
        hook = urldict[url]
        try:
            Gamestop(url, hook)
        except Exception as e:
            print("Some error ocurred parsing Gamestop: ", e)
        time.sleep(10)


def targetfunc(url):
    while True:
        hook = urldict[url]
        try:
            Target(url, hook)
        except Exception as e:
            print("Some error ocurred parsing Target: ", e)
        time.sleep(10)

def bhfunc(url):
    while True:
        hook = urldict[url]
        try:
            BH(url, hook)
        except Exception as e:
            print("Some error ocurred parsing BH Photo: ", e)
        time.sleep(10)

def bestbuyfunc(sku):
    while True:
        hook = bbdict[sku]
        try:
            BestBuy(sku, hook)
        except Exception as e:
            print("Some error ocurred parsing Best Buy: ", e)
        time.sleep(10)

def walmartfunc(url):
    while True:
        hook = urldict[url]
        try:
            Walmart(url, hook)
        except Exception as e:
            print("Some error ocurred parsing WalMart: ", e)
        time.sleep(10)


# MAIN EXECUTION

for url in amazonlist:
    t = Thread(target=amzfunc, args=(url,))
    t.start()
    time.sleep(0.5)

for url in gamestoplist:
    t = Thread(target=gamestopfunc, args=(url,))
    t.start()
    time.sleep(0.5)

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
