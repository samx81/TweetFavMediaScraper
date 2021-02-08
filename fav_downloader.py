from selenium import webdriver
from bs4 import BeautifulSoup
import re, pickle, itertools 
import time, os
import argparse
import pprint as pp
from getpass import getpass
import pandas as pd

from urllib.request import urlretrieve
from tqdm.auto import tqdm
import importlib  
TwitterDownloader = importlib.import_module("twitter-video-downloader.twitter-dl")


parser = argparse.ArgumentParser()
parser.add_argument('username')
parser.add_argument('-n', default=99999 , type=int, help='Nums scroller will scroll')
parser.add_argument('-o', '--out_dir', default='images')
parser.add_argument('-r', '--retry', default=10, type=int, help='Nums scroller will retry when no new items.')
parser.add_argument('--byfolder', action='store_true')
parser.add_argument('--skipvid', action='store_true')
parser.add_argument('-q', '--quality', default='best', choices=['small','medium','large','best'])

def glance(d, n):
    return dict(itertools.islice(d.items(), n))

def get_tweet_height(tweet):
    try:
        style = tweet['style']
    except:
        print('incomplete')
        return 0
    title_search = re.search('translateY\((.*)px', style, re.IGNORECASE)
    if title_search:
        i = title_search.group(1)
    return i

def prettydict(data):
    return pd.DataFrame.from_dict(data, orient='index', columns=['url']).rename_axis('height').to_markdown(tablefmt='github')

class Config:
    textcss = 'css-1dbjc4n r-1iusvr4 r-16y2uox r-1777fci r-1mi0q7o'
    linkcss = 'css-4rbku5 css-18t94o4 css-901oao r-m0bqgq r-1loqt21 r-1q142lx r-1qd0xha r-a023e6 r-16dba41 r-ad9z0x r-bcqeeo r-3s2u2q r-qvutc0'
    imgsetcss = 'css-1dbjc4n r-1bs4hfb r-1867qdf r-1phboty r-rs99b7 r-156q2ks r-1ny4l3l r-1udh08x r-o7ynqc r-6416eg'
    bar_format = "{desc}{postfix} |{bar}|{percentage:3.0f}% [{n_fmt}/{total_fmt}: {elapsed}<{remaining}]"

class MediaDownloader:
    _quality = ['small','medium','large','4096x4096'] # image
    _video_quality = [360,540,720,9999]
    downloaded, skipped, error = [0]* 3
    incomplete = {}
    nomedia = {}
    
    textcss = Config.textcss
    linkcss = Config.linkcss
    imgsetcss = Config.imgsetcss
    twitter_dl = TwitterDownloader.TwitterDownloader('https://twitter.com/ChikozanZoo/status/1356552721092939776',target_width=9999,debug=2)


    def __init__(self, tweetdict, rootdir, quality, skipvideo):
        self.tweetdict = tweetdict
        self.rootdir = rootdir
        self.quality = self._quality[quality]
        self.video_quality = self._video_quality[quality]
        self.skipvideo = skipvideo
        if not os.path.isdir(rootdir+'/'):
            os.mkdir(rootdir+'/') 

    def get_images(self, imgset, author, texts, tweet):
        try:
            imgset = imgset.find_all('a')
            set_size = len(imgset)
            
            for img in imgset:
                img_info  = img['href'].split('/')
                
                file_link = img.find('img')['src']
                file_link = file_link[:file_link.rindex('=')+1] + self.quality
                
                file_info = file_link.split('?')[-1].split("&")
                
                if set_size != 1:
                    fname = f'{author}/{img_info[-3]}_{img_info[-1]}.{file_info[0][7:]}'
                else:
                    fname = f'{author}/{img_info[-3]}.{file_info[0][7:]}'
                
                if 'privatter' in texts.lower():
                    tqdm.write(f'Privatter detected: ' +
                              f'https://twitter.com/{author}/status/{img_info[-3]}')
                
                if os.path.isfile(self.rootdir+'/'+fname):
                    self.skipped += 1
                    continue
                    
                time.sleep(.3)    
                urlretrieve(file_link, self.rootdir+'/'+fname)
                self.downloaded += 1
        except Exception as e:
            if str(e) == "'NoneType' object has no attribute 'find_all'":
                errorlink = tweet.find('a', {'class':self.linkcss})['href']
                tqdm.write(f'{str(e)}  {errorlink}')
            else:
                tqdm.write(f'{e} {str(get_tweet_height(tweet))} https://twitter.com/{author}/status/{img_info[-3]}')
            i = get_tweet_height(tweet)
            self.incomplete[i] = f'https://twitter.com/{author}/status/{img_info[-3]}'
            self.error += 1

    def get_video(self, link, video, tweet):
        tqdm.write(f'Video found: {link}', end='')
        linkinfo = link.split('/')
        videodir = f'{self.rootdir}/{linkinfo[-3]}/{linkinfo[-1]}'
        if os.path.isdir(videodir) and os.listdir(videodir):
            tqdm.write(' Video existed, skip.')
            self.skipped += 1
            return
            
        if video.find('video', {'src': re.compile(r'^(?!blob)')}): # GIF exists
            tqdm.write(' Type: GIF.')
            gif_link = video.find('video')['src']
            if os.path.isfile(f"{self.rootdir}/{linkinfo[-3]}/{linkinfo[-1]}.{gif_link.split('.')[-1]}"):
                self.skipped+=1
                return
            urlretrieve(gif_link, f"{self.rootdir}/{linkinfo[-3]}/{linkinfo[-1]}.{gif_link.split('.')[-1]}")
        elif self.skipvideo:
            tqdm.write('')
            skipped += 1
            return
        else: # Normal Video
            self.twitter_dl.__init__(link, output_dir=f'{self.rootdir}', target_width=self.video_quality)
            try:
                tqdm.write('\n')
                self.twitter_dl.download()
            except Exception as e:
                tqdm.write(f'{str(e)} {link}')
                self.error += 1
                return
        self.downloaded += 1
    
    def download(self):
        t = tqdm(self.tweetdict.values(),bar_format=Config.bar_format)
        for tweet in t:
            t.set_postfix_str(f'Success: {self.downloaded}, Skipped: {self.skipped}, Error: {self.error}')
            
            # Do some need to try here?
            try:
                tweettime = tweet.find('time')['datetime'].split('T')[0]
                textblock = tweet.find('div', {'class':self.textcss}).div.next_sibling.div.div
                texts = textblock.get_text() if textblock else ""
                imgset = tweet.find('div', {'class':self.imgsetcss}) # this and next may not need to try
                video = tweet.find('div', {'data-testid':'videoPlayer'})
                
                authorinfo = tweet.find('a', {'class':self.linkcss})['href'].split('/')[1:] # Throw away empty [0]
                author = authorinfo[0]
                link = f'https://twitter.com/{author}/status/{authorinfo[-1]}'
            except Exception as e:
                i = get_tweet_height(tweet)
                self.incomplete[i] = ''
                tqdm.write(f'{str(e)}, @ height {i}, source incomplete?')
                continue
                
            if not os.path.isdir(f'{self.rootdir}/{author}'):
                os.mkdir(f'{self.rootdir}/{author}')
                
            t.set_description_str(f"Progressing Tweet @ {tweettime}")
            
            # Video Exists!
            if video != None:
                self.get_video(link, video, tweet)
            elif imgset != None:
                self.get_images(imgset, author, texts, tweet)
            else:
                self.nomedia[get_tweet_height(tweet)] = link
                
        if self.incomplete:
            print('[-] Incomplete tweet at:')
            print(prettydict(self.incomplete))
        if self.nomedia:
            print('[-] Not media tweets:')
            print(prettydict(self.nomedia))


def scroller(url, scroll_n, retry_n):
    # Twitter Login
    if os.path.isfile('logincookies.pkl'):
        browser.get('https://www.twitter.com/')
        cookies = pickle.load(open("logincookies.pkl", "rb"))
        for cookie in cookies:
            browser.add_cookie(cookie)
    else:
        browser.get('https://www.twitter.com/login')

        time.sleep(1.5)
        loginname = input('This will login your twitter account on selenium.')
        password = getpass()
        browser.find_element_by_name('session[username_or_email]').send_keys(loginname)
        browser.find_element_by_name('session[password]').send_keys(password)
        browser.find_element_by_css_selector("div[data-testid='LoginForm_Login_Button']").click()
        time.sleep(3)

        pickle.dump( browser.get_cookies() , open("logincookies.pkl","wb"))

    browser.get(url)
    time.sleep(5)

    tweetdict = {}
    last_item = ''
    traverse_history = []
    retry = 0
    for n in range(scroll_n):
        tweets = BeautifulSoup(browser.page_source, "html.parser").select('section[role = "region"]')[0].div.div
        tlen = len(tweets.contents)
        traverse_history.clear()
        count = 0
        for t in reversed(tweets.contents):
            i = get_tweet_height(t)
            if i in tweetdict.keys():
                continue
            traverse_history.append(i)
            tweetdict[int(i)] = t
        print(f'  {traverse_history[0]} {n}', end="\r")
        if last_item == traverse_history[0]:
            retry += 1
            print(f'  No new items, Retry: {retry}', end="\r")
            time.sleep(retry*2.5)
            if retry >= 10:
                print("Retried for 3 times, Seems to reached the end, Quit Scrolling")
                break
        else:
            last_item = traverse_history[0]
            retry = 0
        browser.execute_script("window.scrollTo(0, {})".format(traverse_history[0]))
        time.sleep(2)

    browser.quit()
    tweetdict = dict(sorted(tweetdict.items(), key=lambda item: item[0]))
    return tweetdict

if __name__ == '__main__':
    args = parser.parse_args()
    print(args.out_dir)
    path_to_chromedriver ="./geckodriver"            #enter path of chromedriver
    browser = webdriver.Firefox(executable_path = path_to_chromedriver)
    url = 'https://twitter.com/{}/likes'.format(args.username)
    
    
    qualitymap = {'small':0, 'medium':1, 'large':2, 'best':3}
    tweets = scroller(url, args.n, args.retry)
    media_downloader = MediaDownloader(tweets,args.out_dir, qualitymap[args.quality], args.skipvid)
    media_downloader.download()
