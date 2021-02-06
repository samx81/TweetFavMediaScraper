from selenium import webdriver
from bs4 import BeautifulSoup
import re, pickle, itertools 
import time, io, os
import pprint as pp
from getpass import getpass

from urllib.request import urlretrieve
from tqdm.auto import tqdm
def glance(d, n):
    return dict(itertools.islice(d.items(), n))

def scroller(url):
    # Twitter Login
    if os.path.isfile('cookies.pkl'):
        browser.get('https://www.twitter.com/')
        cookies = pickle.load(open("cookies.pkl", "rb"))
        for cookie in cookies:
            browser.add_cookie(cookie)
    else:
        browser.get('https://www.twitter.com/login')

        time.sleep(1.5)
        password = getpass()
        browser.find_element_by_name('session[username_or_email]').send_keys('username')
        browser.find_element_by_name('session[password]').send_keys(password)
        browser.find_element_by_css_selector("div[data-testid='LoginForm_Login_Button']").click()
        time.sleep(3)

        pickle.dump( browser.get_cookies() , open("cookies.pkl","wb"))

    browser.get(url)
    time.sleep(3)

    tweetdict = {}
    for n in range(50):
        tweets = BeautifulSoup(browser.page_source, "html.parser").select('section[role = "region"]')[0].div.div
        tlen = len(tweets.contents)
        theight = []
        count = 0
        for t in reversed(tweets.contents):
            title_search = re.search('translateY\((.*)px', t['style'], re.IGNORECASE)
            if title_search:
                i = title_search.group(1)
                if i in tweetdict.keys():
                    continue
                theight.append(i)
                tweetdict[int(i)] = t
        # print(tweetdict.keys())
        browser.execute_script("window.scrollTo(0, {})".format(theight[0]))
        time.sleep(1)

    browser.quit()
    tweetdict = dict(sorted(tweetdict.items(), key=lambda item: item[0]))
    return tweetdict

def img_downloader(tweetdict, rootdir='images'):
    
    downloaded, skipped, error = [0]* 3
    linkcss = 'css-4rbku5 css-18t94o4 css-901oao r-m0bqgq r-1loqt21 r-1q142lx r-1qd0xha r-a023e6 r-16dba41 r-ad9z0x r-bcqeeo r-3s2u2q r-qvutc0'
    imgsetcss = 'css-1dbjc4n r-1bs4hfb r-1867qdf r-1phboty r-rs99b7 r-156q2ks r-1ny4l3l r-1udh08x r-o7ynqc r-6416eg'
    
    if not os.path.isdir(rootdir+'/'):
        os.mkdir(rootdir+'/')  
    
    t = tqdm(tweetdict.values())
    for tweet in t:
        t.set_description_str(f'Success: {downloaded}, Skipped: {skipped}, Error:{error}____')
        authorinfo = tweet.findChild('a', {'class':linkcss})['href'].split('/')[1:] # Throw away empty [0]
        author = authorinfo[0]
        if not os.path.isdir(rootdir+'/'+author):
            os.mkdir(rootdir+'/'+author)

        imgset = tweet.findChild('div', {'class':imgsetcss})
        try:
            imgset = imgset.findChildren('a')
            set_size = len(imgset)
            
            for img in imgset:
                img_info  = img['href'].split('/')
                
                file_link = img.findChild('img')['src']
                file_link = file_link[:file_link.rindex('=')+1]+'4096x4096'
                
                file_info = file_link.split('?')[-1].split("&")
#                 print(img_info)
                
                if set_size != 1:
                    fname = f'{author}/{img_info[-3]}_{img_info[-1]}.{file_info[0][7:]}'
                else:
                    fname = f'{author}/{img_info[-3]}.{file_info[0][7:]}'
                
                if os.path.isfile(rootdir+'/'+fname):
                    skipped += 1
                    continue
                    
                time.sleep(.3)    
                urlretrieve(file_link, rootdir+'/'+fname)
                downloaded += 1
                
        except Exception as e:
            if str(e) == "'NoneType' object has no attribute 'findChildren'":
                errorlink = tweet.findChild('a', {'class':linkcss})['href']
                tqdm.write(f'{str(e)}  {errorlink}')
            else:
                tqdm.write(f'{str(e)} {"".join(authorinfo)}')
            error += 1
            continue

if __name__ == '__main__':
    path_to_chromedriver ="./geckodriver"            #enter path of chromedriver
    browser = webdriver.Firefox(executable_path = path_to_chromedriver)
    url = 'https://twitter.com/username/likes'
    count = 4
    tweets = scroller(url)
    img_downloader(tweets)
