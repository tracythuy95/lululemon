import requests
from bs4 import BeautifulSoup
from requests_html import AsyncHTMLSession
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import time
import pandas as pd
import csv
import json
import numpy as np
import seaborn as sns
import pickle
import urllib

def add_reviews(stars):
    total = 0
    for x in stars:
        total+=int(x)
    return(total)

def avg_stars(stars):
    i = 5
    score = 0
    total = 0
    for x in stars: 
        score +=(int(x)*i)
        total+=int(x)
        i-=1

    if score == 0 | total == 0:
        return(0)
    return(score/total)

def split_percent(material):
    if material == ['None listed']:
        return(material)
    
    new_list = []
    for x in material:
        new_list.append(x.split('% ')[1])
        
    new_list = sorted(list(set(new_list)))
    return(new_list)

def review_materials(product_urls, driver_path):
    '''

    function: review_materials
    inputs: 
        - product_url: list of product urls (urls to specific item)
        - driver: this is path to the Chrome driver
    outputs:
    - df
        - url: url to specific product
        - stars: list of number review for each star
        - 

        * for prices, if there is a range, then the lowest value will be returned

    '''
    driver = webdriver.Chrome(driver_path)

    cols = ['url', 'stars', 'material', 'features']
    lst = []

    t = 0
    for url in product_urls:
        stars = []
        material = []
        features = []
        
        driver.get(url)
        
        # 
        i = 0
        while features == []:
            features = [i.get_attribute("innerHTML").replace(",", "").strip() for i in driver.find_elements_by_xpath('.//span[@class="product-education-accordions__attributes__item__flex"]')]
            i+=1
            if(i==4):
                features = ['None listed']
        
        i = 0
        while material == []:
            material = [i.get_attribute("innerHTML").replace(",", "").strip() for i in driver.find_elements_by_xpath('.//dd[@class="product-education-accordions__attributes__item__list"]')]
            i+=1
            if(i==4):
                material = ['None listed']

        i = 0
        while stars == []:
            if i == 10:
                stars = ['0', '0', '0', '0', '0']
                break
            try:
                button = driver.find_element_by_xpath("//span[text()='Reviews']")
                actions = ActionChains(driver)
                actions.move_to_element(button).perform()  # move button into view
                button.click()  
                stars = [i.get_attribute("data-bv-histogram-rating-count") for i in driver.find_elements_by_xpath('.//div[@class="bv-inline-histogram-ratings-bar"]')]      
                i+=1
            except: 
                i+=1
            

        lst.append([url, stars, material, features])

    df = pd.DataFrame(lst, columns=cols)
    
    df['total_reviews']  = df['stars'].apply(lambda x: add_reviews(x))
    df['avg_rating'] = df['stars'].apply(lambda x: avg_stars(x))

    df['material_clean'] = df['material'].apply(lambda x: split_percent(x))
    df['material_clean_list'] = [','.join(map(str, l)) for l in df['material_clean']]

    df['features_list'] = [','.join(map(str, l)) for l in df['features']]

    df[['five_stars','four_stars', 'three_stars', 'two_stars', 'one_stars']] = pd.DataFrame(df.stars.tolist(), index= df.index)

    driver.close()

    return(df)

def product_url(page_url, driver_path):
    '''
    function: product_url
    inputs: 
    - page_url: product type page url such as women's tops or men's pants
    - driver: this is path to the Chrome driver
    outputs:
    - df
        - product_name: item name
        - url: url to specific product
        - type: type of product (shirt, pants, long-sleeve, etc)
        - current_price: current listed price*
        - old_price: original price*
        
        * for prices, if there is a range, then the lowest value will be returned
    '''
    driver = webdriver.Chrome(driver_path)

    driver.get(page_url)  # open WMTM page
    i = 0
    while True:
        try:
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight + 1000);')  
            time.sleep(15)  
            button = driver.find_element_by_xpath("//span[text()='View more products']")
            actions = ActionChains(driver)
            actions.move_to_element(button).perform()  # move button into view
            button.click()  
            time.sleep(15) 
        
        except NoSuchElementException:  # all products loaded
            break

    try:
        pickle.dump(driver.page_source , open( "page_source_1", "wb" ) )
        product_urls = [(i.get_attribute('href')).split("?", 1)[0] for i in driver.find_elements_by_xpath('.//div[@class="product-tile"]//a')]
    except AttributeError:
        try:
            time.sleep(15) 
            pickle.dump(driver.page_source , open( "page_source_2", "wb" ) )
            product_urls = [(i.get_attribute('href')).split("?", 1)[0] for i in driver.find_elements_by_xpath('.//div[@class="product-tile"]//a')]
        except AttributeError: 
            time.sleep(15) 
            pickle.dump(driver.page_source , open( "page_source_3", "wb" ) )
            product_urls = [(i.get_attribute('href')).split("?", 1)[0] for i in driver.find_elements_by_xpath('.//div[@class="product-tile"]//a')]

    product_urls = list(dict.fromkeys(product_urls))

    product_name = [ urllib.parse.unquote(json.loads(i.get_attribute('data-lulu-attributes'))['product']['name']) for i in driver.find_elements_by_xpath('.//h3[@class="product-tile__product-name lll-text-body-1"]//a')]
    price = [i.get_attribute("innerText").replace("\xa0\n", "").replace("\xa0-\xa0", "-") for i in driver.find_elements_by_xpath('.//span[@class="price-1SDQy price"]')]

    df = pd.DataFrame()
    df['product_name'] = product_name
    try:
        df['url'] = product_urls
        df['type'] = df['url'].str.split('/').str[4]
        df['price'] = price
    except ValueError:
        time.sleep(30) 
        df['url'] = product_urls
        df['type'] = df['url'].str.split('/').str[4]
        df['price'] = price
    
    ### if-else statement in case there are no discounted items (then there is no "Regular price/ Sales price to split on" )
    if(df['price'].str.contains('Regular').any()):
        new = df["price"].str.split("Regular Price", n = 1, expand = True)
        df["current_price"] = new[0].str.replace('Sale Price','')
        df["old_price"]= new[1] 

    else:
        df['current_price'] = df['price']
        df['old_price'] = df['price']

    df['current_price'] = df['current_price'].str.split('-').str[0].str.replace("$", "")

    df['old_price'] = df['old_price'].fillna(df['current_price'])
    df['old_price'] = df['old_price'].str.split('-').str[0].str.replace("$", "")

    df['current_price'] = pd.to_numeric(df['current_price'])
    df['old_price'] = pd.to_numeric(df['old_price'])
    df = df.drop(['price'], axis = 1)
    
    driver.close()

    return(df)

def main():

    csv_file = pd.read_csv('/Users/tracynguyen/Documents/GitHub/lululemon/resources/lululemon_url.csv')

    csv_filter = csv_file[csv_file['type'] == 'leggings']

    # page_url_list = [w_bra]
    
    page_url_list = list(csv_filter['url'])

    driver_path = '/Users/tracynguyen/Applications/chromedriver'

    dfs = []
    for page_url in page_url_list:
        print("start on: " + page_url )
        df = product_url(page_url, driver_path)
        print('done with phase 1')

        product_urls = list(df['url'])
        df1 = review_materials(product_urls, driver_path)
        print('done with phase 2')

        merge_df = pd.merge(df, df1, on = 'url')
        print('done!!')
        dfs.append(merge_df)

    final_df = pd.concat(dfs, ignore_index=True)
    pickle.dump(final_df, open( "20210209_women_tmp", "wb" ) )


if __name__=="__main__":
    main()