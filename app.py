import requests
from requests_oauthlib import OAuth1
import re
import random
import configparser
import httplib2
import goslate
import hashlib
import time
from datetime import datetime
import twstock
import json,time,sys
import pandas
import http.client
import pytz

from twstock import Stock
from twstock import BestFourPoint

from bs4 import BeautifulSoup
from googletrans import Translator
from google.cloud import translate
from google.oauth2 import service_account

#from yahooweather import YahooWeather, UNIT_C, get_woeid

from flask import Flask, request, abort
from flask_mail import Mail, Message

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models import (
    MessageEvent,TextMessage,TextSendMessage,ImageSendMessage,
    SourceUser,TemplateSendMessage,ConfirmTemplate,BaseSize,ImagemapArea,
    ButtonsTemplate,ImagemapSendMessage,MessageTemplateAction,MessageImagemapAction,
    StickerMessage,StickerSendMessage,LocationMessage,LocationSendMessage,
    ImageMessage,VideoMessage,AudioMessage,UnfollowEvent,URIImagemapAction,
    FollowEvent, JoinEvent, LeaveEvent, BeaconEvent,VideoSendMessage
)

import os
import psycopg2
import urllib.parse as urlparse

app = Flask(__name__)

# Channel Access Token
chl_token = os.environ['CHANNEL_ACCESS_TOKEN']
line_bot_api = LineBotApi(chl_token)

# Yahoo Weather Key & Secret
client_key = os.environ['WEATHER_CLIENT_KEY']
client_secret = os.environ['WEATHER_CLIENT_SECRET']

# Google Cloud API

#credentials_raw = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
#service_account_info = json.loads(credentials_raw)
#credentials = service_account.Credentials.from_service_account_info(service_account_info)

# Channel Secret
hook_hdler = os.environ['WEBHOOK_HANDLER']
handler = WebhookHandler(hook_hdler)

#config = configparser.ConfigParser()

cweather={"Tornado":"龍捲風","Tropical Storm":"颱風","Hurricane":"颶風","Severe Thunderstorms":"大暴雷","ThunderStorms":"暴雷",
         "Mixed Rain And Snow":"雨和雪","Mixed Snow And Sleet":"雪和霰","Freezing Drizzle":"凍毛雨","Drizzle":"毛毛雨","Rain":"雨",
         "Freezing Rain":"凍雨","Showers":"陣雨","Snow Flurries":"雪花","Light Snow Showers":"小雪花","Snow":"下雪","Blowing Snow":"吹雪",
         "Snow Flurries":"雪花","Hail":"冰雹","Sleet":"霰","Dust":"灰塵","Foggy":"有霧","Haze":"陰霾","Smoky":"多煙","Blustery":"大風",
         "Windy":"有風","Cold":"寒冷","Cloudy":"雲","Mostly Cloudy":"多雲","Partly Cloudy":"偶雲","Clear":"晴朗","Sunny":"有陽光",
         "Fair":"晴天","Mixed Rain And Hail":"雨冰雹","Hot":"熱","Isolated Thunderstorms":"雷暴","Scattered Thunderstorms":"偶雷暴",
         "Scattered Showers":"偶陣雨","Thundershowers":"暴雨","Isolated Thundershowers":"暴雨","Breezy":"微風","Mostly Sunny":"多晴",
         "Rain And Snow":"雨和雪","Snow Showers":"陣雪","Mostly Clear":"晴時偶雲","Thunderstorms":"雷暴"}

cmonth={"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06","Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}

def getYahooWeather(lat,lon):
    query_url = 'https://weather-ydn-yql.media.yahoo.com/forecastrss?lat='+str(lat)+'&lon='+str(lon)+'&format=json&u=c'
    print(query_url)
    queryoauth = OAuth1(client_key, client_secret, signature_type='query')
    r = requests.get(url=query_url, auth=queryoauth)
    result = json.loads(r.content.decode("utf-8"))
    return result
    
def connect_db():
    DATABASE_URL = os.environ['DATABASE_URL']
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def create_how():
    sql = "CREATE TABLE how (key TEXT PRIMARY KEY, value TEXT not NULL, uid TEXT, memo TEXT)"    
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute(sql)
        cur.close()
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return
  
def insert_how(kk,vv,uu,mm):
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO how(key,value,uid,memo) VALUES(%s,%s,%s,%s)",(kk,vv,uu,mm))
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return

def update_how(kk,vv,uu,mm):
    conn = None
    updated_rows = 0
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("UPDATE how SET value = %s, uid=%s, memo= %s WHERE key =%s",(vv,uu,mm,kk))
        updated_rows = cur.rowcount
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return updated_rows   

def turnoff_trans(dd):
    conn = None
    updated_rows = 0
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("UPDATE config SET Isofftrans = 'Y'  WHERE sysname =%s",(dd,))
        updated_rows = cur.rowcount
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return updated_rows 

def turnon_trans(dd):
    conn = None
    updated_rows = 0
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("UPDATE config SET Isofftrans = 'N'  WHERE sysname =%s",(dd,))
        updated_rows = cur.rowcount
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return updated_rows 

def isoff_trans(dd):
    conn = None
    
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT Isofftrans,Issleep FROM config WHERE sysname = %s",(dd,))
        
        print("dd:{}".format(dd))
        print("cur.rowcount={}".format(cur.rowcount))
        if (int)(cur.rowcount) != 0:
            row = cur.fetchone()
            row1 = row
            while row is not None:
                row = cur.fetchone()
        else:
            cur.execute("INSERT INTO config(sysname,Issleep,Isofftrans) VALUES(%s,'N','N')",(dd,))
            conn.commit()
            row1 = 'N','N'
        
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return row1

def query_config(kk):
    conn = None
    
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT Isofftrans,Issleep FROM config WHERE sysname=%s",(kk,))
        row = cur.fetchone()
        cnt = cur.rowcount
        row1 = row
 
        while row is not None:
            row = cur.fetchone()
 
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return cnt, row1

def query_sentence():
    conn = None
    
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sentence ORDER BY random() LIMIT 1")
        row = cur.fetchone()
        cnt = cur.rowcount
        row1 = row
 
        while row is not None:
            row = cur.fetchone()
 
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return cnt, row1

def insert_config_N(kk):
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO config(sysname,Issleep,Isofftrans) VALUES(%s,'N','N')",(kk,))
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return

def query_how(kk):
    conn = None
    
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT key,value,uid,memo FROM how WHERE key=%s",(kk,))
        print("The number of rows: ", cur.rowcount)
        row = cur.fetchone()
        row1 = row
 
        while row is not None:
            print(row)
            row = cur.fetchone()
 
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return cur.rowcount, row1

def delete_how(kk):
    conn = None
    rows_deleted = 0
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM how WHERE key = %s", (kk,))
        rows_deleted = cur.rowcount
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
    return rows_deleted

def get_Qna_answer(q_text):  #關閉Azure上建立的QnA Service, 這個目前不能用了
    try:
        host = "https://linebird.azurewebsites.net/qnamaker"
        endpoint_key = "7073b95a-77ad-4063-8c5a-3392ca6da288"
        route = " /knowledgebases/4807b54f-d5b8-48b8-b5c9-123a8ecd0e3a/generateAnswer"
        question = {"question": q_text,"top": 3}
        headers = {
            'Authorization': 'EndpointKey 7073b95a-77ad-4063-8c5a-3392ca6da288',
            'Content-Type': 'application/json',
            'Content-Length': len(q_text)
        }
        conn = http.client.HTTPSConnection(host,port=443)
        print("go here 00")
        conn.request ("POST", route,  question, headers)
        print("go here 0")
        response = conn.getresponse ()
        print("go here 1")
        daga = response.read ()
        print("go here 2")
        print(json.dumps(json.loads(data), indent=4))
        print("go here 3")
        return data['answers'][0]['answer']
    except:
        print ("Unexpected error:", sys.exc_info()[0])
        print ("Unexpected error:", sys.exc_info()[1])
        return "Error"

class Dict:
    in_String = "沒有文字"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0',
            'Referer': 'http://fanyi.youdao.com/',
            'contentType': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        self.url = 'http://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule&sessionFrom='
        self.base_config()
       
    def base_config(self):
        s.get('http://fanyi.youdao.com/')
    
    def translate(self):
        i = self.in_String
        salf = str(int(time.time() * 1000) + random.randint(0, 9))
        n = 'fanyideskweb' + i + salf + "rY0D^0'nM0}g5Mm1z%1G4"
        m.update(n.encode('utf-8'))
        sign = m.hexdigest()
        data = {
            'i': i,
            'fromLang': 'AUTO',
            'toLang': 'AUTO',
            'smartresult': 'dict',
            'client': 'fanyideskweb',
            'salt': salf,
            'sign': sign,
            'doctype': 'json',
            'version': "2.1",
            'keyfrom': "fanyi.web",
            'action': "FY_BY_DEFAULT",
            'typoResult': 'true'
        }
        resp = s.post(self.url, headers=self.headers, data=data)
        return resp.json()

def youdao_translate(text):
    s = requests.Session()
    m = hashlib.md5()
    my_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0',
            'Referer': 'http://fanyi.youdao.com/',
            'contentType': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
    my_url = 'http://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule&sessionFrom='
    s.get('http://fanyi.youdao.com/')
    i = text
    salf = str(int(time.time() * 1000) + random.randint(0, 9))
    n = 'fanyideskweb' + i + salf + "rY0D^0'nM0}g5Mm1z%1G4"
    m.update(n.encode('utf-8'))
    sign = m.hexdigest()
    my_data = {
        'i': i,
        'fromLang': 'zh-TW',
        'toLang': 'en',
        'smartresult': 'dict',
        'client': 'fanyideskweb',
        'salt': salf,
        'sign': sign,
        'doctype': 'json',
        'version': "2.1",
        'keyfrom': "fanyi.web",
        'action': "FY_BY_DEFAULT",
        'typoResult': 'true'
    }
    resp = s.post(url=my_url, headers=my_headers, data=my_data)
    return resp.json()

def getSticker():
    aa=([1,1],[1,2],[1,3],[1,4],[1,5],[1,6],[1,7],[1,8],[1,9],[1,10],
        [1,11],[1,12],[1,13],[1,14],[1,15],[1,16],[1,17],[1,21],[1,100],[1,101],
        [1,102],[1,103],[1,104],[1,105],[1,106],[1,107],[1,108],[1,109],[1,110],[1,111],
        [1,112],[1,113],[1,114],[1,115],[1,116],[1,117],[1,118],[1,119],[1,120],[1,121],
        [1,122],[1,123],[1,124],[1,125],[1,126],[1,127],[1,128],[1,129],[1,130],[1,131],
        [1,132],[1,133],[1,134],[1,135],[1,136],[1,137],[1,138],[1,139],[1,401],[1,402],
        [1,403],[1,404],[1,405],[1,406],[1,407],[1,408],[1,409],[1,410],[1,411],[1,412],
        [1,413],[1,414],[1,415],[1,416],[1,417],[1,418],[1,419],[1,420],[1,421],[1,422],
        [1,423],[1,424],[1,425],[1,426],[1,427],[1,428],[1,429],[1,430])
    bb=([2,18],[2,19],[2,20],[2,22],[2,23],[2,24],[2,25],[2,26],[2,27],[2,28],
        [2,29],[2,30],[2,31],[2,32],[2,33],[2,34],[2,35],[2,36],[2,37],[2,38],
        [2,39],[2,40],[2,41],[2,42],[2,43],[2,44],[2,45],[2,46],[2,47],[2,140],
        [2,141],[2,142],[2,143],[2,144],[2,145],[2,146],[2,147],[2,148],[2,149],[2,150],
        [2,151],[2,152],[2,153],[2,154],[2,155],[2,156],[2,157],[2,158],[2,159],[2,160],
        [2,161],[2,162],[2,163],[2,164],[2,165],[2,166],[2,167],[2,168],[2,169],[2,170],
        [2,171],[2,172],[2,173],[2,174],[2,175],[2,176],[2,177],[2,178],[2,179],[2,501],
        [2,502],[2,503],[2,504],[2,505],[2,506],[2,507],[2,508],[2,509],[2,510],[2,511],
        [2,522],[2,523],[2,524],[2,525],[2,526],[2,527])
    cc=([3,180],[3,181],[3,182],[3,183],[3,184],[3,185],[3,186],[3,187],[3,188],[3,189],
        [3,190],[3,191],[3,192],[3,193],[3,194],[3,195],[3,196],[3,197],[3,198],[3,199],
        [3,200],[3,201],[3,202],[3,203],[3,204],[3,205],[3,206],[3,207],[3,208],[3,209],
        [3,210],[3,211],[3,212],[3,213],[3,214],[3,215],[3,216],[3,217],[3,218],[3,219],
        [3,220],[3,221],[3,222],[3,223],[3,224],[3,225],[3,226],[3,227],[3,228],[3,229],
        [3,230],[3,231],[3,232],[3,233],[3,234],[3,235],[3,236],[3,237],[3,238],[3,239],
        [3,240],[3,241],[3,242],[3,243],[3,244],[3,245],[3,246],[3,247],[3,248],[3,249],
        [3,250],[3,251],[3,252],[3,253],[3,254],[3,255],[3,256],[3,257],[3,258],[3,259])
    dd=([11537,52002734],[11537,52002735],[11537,52002736],[11537,52002737],[11537,52002738],[11537,52002739],
        [11537,52002740],[11537,52002741],[11537,52002742],[11537,52002743],[11537,52002744],[11537,52002745],
        [11537,52002746],[11537,52002747],[11537,52002748],[11537,52002749],[11537,52002750],[11537,52002751],
        [11537,52002752],[11537,52002753],[11537,52002754],[11537,52002755],[11537,52002756],[11537,52002757],
        [11537,52002758],[11537,52002759],[11537,52002760],[11537,52002761],[11537,52002762],[11537,52002763],
        [11537,52002764],[11537,52002765],[11537,52002766],[11537,52002767],[11537,52002768],[11537,52002769],
        [11537,52002770],[11537,52002771],[11537,52002772],[11537,52002773],[11538,51626494],[11538,51626495],
        [11538,51626496],[11538,51626497],[11538,51626498],[11538,51626499],[11538,51626500],[11538,51626501],
        [11538,51626502],[11538,51626503],[11538,51626504],[11538,51626505],[11538,51626506],[11538,51626507],
        [11538,51626508],[11538,51626509],[11538,51626510],[11538,51626511],[11538,51626512],[11538,51626513],
        [11538,51626514],[11538,51626515],[11538,51626516],[11538,51626517],[11538,51626518],[11538,51626519],
        [11538,51626520],[11538,51626521],[11538,51626522],[11538,51626523],[11538,51626524],[11538,51626525],
        [11538,51626526],[11538,51626527],[11538,51626528],[11538,51626529],[11538,51626530],[11538,51626531],
        [11538,51626532],[11538,51626533])
    
    sticker=aa+bb+cc+dd
    
    idx =random.randint(0,len(sticker))
    return sticker[idx][0],sticker[idx][1]

def FullToHalf(ustring):
    n=[]
    for s in ustring:
        rstring = ""
        for uchar in s:
            inside_code = ord(uchar)
            if inside_code == 12288:
                inside_code = 32
            elif (inside_code >= 65281 and inside_code <= 65374):
                inside_code -= 65248
            
            rstring += chr(inside_code)
            n.append(rstring)
            
    return ''.join(n)


def technews():
    target_url = 'https://technews.tw/'
    
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('article div h1.entry-title a')):
        if index == 12:
            return content
        title = data.text
        link = data['href']
        content += '{}\n{}\n\n'.format(title, link)
    return content

def getOnlinePrice(stockID):
    url = 'https://tw.stock.yahoo.com/q/q?s='+stockID
    conn = httplib2.Http(".cache")
    
    headers = {'Content-type':'application/x-www-form-urlencoded',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
               'User-Agent':'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:34.0) Gecko/20100101 Firefox/34.0'}
    
    resp, doc = conn.request(url, method='GET', body=None, headers=headers)
    
    soup = BeautifulSoup(doc, 'html.parser')
    price = "0.0"
    
    try:
        table = soup.findAll(text='成交')[0].parent.parent.parent
        #title = table.select('tr')[0].select('th')[2].text
        name = table.select('tr')[1].select('td')[0].text[4:6]
        price = table.select('tr')[1].select('td')[2].text
        #result = list([stockID, name, title, price])
    except:
        #result = [stockID, False]
        price = "錯誤"
        name ="錯誤"
    
    return name, price

def translate_text(text, target='en'):
    client = translate.Client()
    result = client.translate(text, target_language=target)
    return result['translatedText']

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def Message_Content(event):
    #print(event)  將此功能移除
    #line_bot_api.reply_message(event.reply_token,StickerSendMessage(package_id=1, sticker_id=2))
    return

@handler.add(MessageEvent, message=StickerMessage)
def Message_Sticker(event):
    pp,ii = getSticker()
    line_bot_api.reply_message(event.reply_token,StickerSendMessage(package_id=pp, sticker_id=ii))
    return
    
@handler.add(MessageEvent, message=LocationMessage)
def Message_Location(event):
    reply_msg = TextMessage(id=event.message.id, text='')
    reply_msg.text = "地址:"+event.message.address+"\n緯度:"+str(event.message.latitude)+"\n經度:"+str(event.message.longitude)
       
    yweather = getYahooWeather(event.message.latitude, event.message.longitude)
    msg1=''
    msg2=''
    fcast = yweather['forecasts']
    print(yweather)
    
    for i in range(len(fcast)):
        print(fcast[i]['day']+'  '+ str(fcast[i]['high'])+'  '+ str(fcast[i]['low'])+'  '+fcast[i]['text'])
        date = str(datetime.fromtimestamp(fcast[i]['date'], tz=pytz.timezone('Asia/Taipei')))
        ctext = cweather.get(fcast[i]['text'],fcast[i]['text'])
        msg2=msg2+ date[5:10] +'{: >5d}'.format(fcast[i]['low'])+'{: >5d}'.format(fcast[i]['high'])+'   '+ ctext +"\n"
    
    
    now = yweather['current_observation']
    nowdate = str(datetime.fromtimestamp(now['pubDate'], tz=pytz.timezone('Asia/Taipei')))
    msg1 = "\n預報時刻:\n"+nowdate[:19]
    msg1 = msg1+"\n現在天氣:\n氣溫:  "+str(now['condition']['temperature'])+"度C\n天候:  " + cweather.get(now['condition']['text'],now['condition']['text']) +"\n濕度:  "+str(now['atmosphere']['humidity'])+"%\n風向:  "+str(now['wind']['direction'])+"度\n風速:  "+str(now['wind']['speed']) + "km/hr" 
    msg1 = msg1+"\n日出:  "+now['astronomy']['sunrise'] + "\n日落:  " + now['astronomy']['sunset']
    reply_msg.text = reply_msg.text + msg1 + "\n\n未來天氣預測:\n 日期  低溫 高溫  天候\n" + msg2
    
    line_bot_api.reply_message(event.reply_token,reply_msg)
    return
    
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    
    print(event)
    reply_msg = event.message
    
    if event.message.text == "今日新聞" or event.message.text == "news" or event.message.text == 'n':
        content = technews()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return
    
    if event.message.text =="群創官網" or event.message.text == "群創" or event.message.text == "innolux":
        msg = "使用方式:\n[#股票代碼]\n[@股票名稱]\n[$數學運算式]\n[&空氣品質]\n[*空品測站]\n[news看新聞]\n[位置資訊->天氣]\n[!抽貼圖]\n[t+要教的句子:回答的句子]\n[?說明]\n[help]"
        reply_msg.text = msg +"\n\n你選到一條不歸路: http://www.innolux.com"
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
    
 
    if event.message.text =="查詢股票資訊" or event.message.text == "stock" or event.message.text=="股票":
        try:
            stock = twstock.realtime.get("3481")
            msg1 = "-=="+stock['info']['name']+"(3481)==-\n目前價格:"+stock['realtime']['latest_trade_price']
            msg2 = msg1+"\n開盤價:"+stock['realtime']['open']+"\n最高價:"+stock['realtime']['high']+"\n最低價:"+stock['realtime']['low']
            msg3 = msg2+"\n累積成交量:"+stock['realtime']['accumulate_trade_volume']
            demo_text = msg3
        except:
            demo_text = "錯誤"
        
        reply_msg.text = demo_text +"\n\n輸入[#股票代碼]方式查詢!"
        
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
        
    if event.message.text =="詢問天氣" or event.message.text=="天氣" or event.message.text =="weather" or event.message.text == 'w' or event.message.text=='W':
        yweather = getYahooWeather('22.999938', '120.225658')
        msg1=''
        msg2=''
        fcast = yweather['forecasts']
        print(yweather)
        for i in range(len(fcast)):
            print(fcast[i]['day']+'  '+ str(fcast[i]['high'])+'  '+ str(fcast[i]['low'])+'  '+fcast[i]['text'])
            date = str(datetime.fromtimestamp(fcast[i]['date'], tz=pytz.timezone('Asia/Taipei')))
            ctext = cweather.get(fcast[i]['text'],fcast[i]['text'])
            msg2=msg2+ date[5:10] +'{: >5d}'.format(fcast[i]['low'])+'{: >5d}'.format(fcast[i]['high'])+'   '+ ctext +"\n"
        
        now = yweather['current_observation']
        nowdate = str(datetime.fromtimestamp(now['pubDate'], tz=pytz.timezone('Asia/Taipei')))
        msg1 = "\n預報時刻:\n"+nowdate[:19]
        msg1 = msg1+ "\n現在天氣:\n氣溫:  "+str(now['condition']['temperature'])+"度C\n天候:  " + cweather.get(now['condition']['text'],now['condition']['text']) +"\n濕度:  "+str(now['atmosphere']['humidity'])+"%\n風向:  "+str(now['wind']['direction'])+"度\n風速:  "+str(now['wind']['speed']) + "km/hr" 
        msg1 = msg1+"\n日出:  "+now['astronomy']['sunrise'] + "\n日落:  " + now['astronomy']['sunset']
        
        reply_msg.text = "--==[台南地區天氣]==--"+ msg1 + "\n\n未來天氣預測:\n 日期  低溫 高溫  天候\n" + msg2
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
    
    if event.message.text == 's' or event.message.text == 'S':
        yweather = getYahooWeather('25.11635', '121.517872')
        msg1=''
        msg2=''
        fcast = yweather['forecasts']
        print(yweather)
        for i in range(len(fcast)):
            print(fcast[i]['day']+'  '+ str(fcast[i]['high'])+'  '+ str(fcast[i]['low'])+'  '+fcast[i]['text'])
            date = str(datetime.fromtimestamp(fcast[i]['date'], tz=pytz.timezone('Asia/Taipei')))
            ctext = cweather.get(fcast[i]['text'],fcast[i]['text'])
            msg2=msg2+ date[5:10] +'{: >5d}'.format(fcast[i]['low'])+'{: >5d}'.format(fcast[i]['high'])+'   '+ ctext +"\n"
        
        now = yweather['current_observation']
        nowdate = str(datetime.fromtimestamp(now['pubDate'], tz=pytz.timezone('Asia/Taipei')))
        msg1 = "\n預報時刻:\n"+nowdate[:19]
        msg1 = msg1+ "\n現在天氣:\n氣溫:  "+str(now['condition']['temperature'])+"度C\n天候:  " + cweather.get(now['condition']['text'],now['condition']['text']) +"\n濕度:  "+str(now['atmosphere']['humidity'])+"%\n風向:  "+str(now['wind']['direction'])+"度\n風速:  "+str(now['wind']['speed']) + "km/hr" 
        msg1 = msg1+"\n日出:  "+now['astronomy']['sunrise'] + "\n日落:  " + now['astronomy']['sunset']
        
        reply_msg.text = "--==[石牌地區天氣]==--"+ msg1 + "\n\n未來天氣預測:\n 日期  低溫 高溫  天候\n" + msg2
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
    
    if event.message.text == "貼圖" or event.message.text == 'sticker':
        line_bot_api.reply_message(event.reply_token,StickerSendMessage(package_id=1, sticker_id=2))
        return
    
    if event.message.text =="位置" or event.message.text == 'location':
        line_bot_api.reply_message(event.reply_token,LocationSendMessage(title='my location', address='Tainan', latitude=22.994821, longitude=120.196452))
        return
    
    if event.message.text == '*' or event.message.text == '＊':
        imagemap_message = ImagemapSendMessage(
            base_url='https://i.imgur.com/Mgvn9AK.jpg',
            alt_text='this is an imagemap',
            base_size = BaseSize(height=480, width=860),
            actions=[
                URIImagemapAction(
                    link_uri='https://taqm.epa.gov.tw/taqm/tw/default.aspx',
                    area=ImagemapArea(
                        x=0, y=0, width=850, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Tamsui',
                    area=ImagemapArea(
                        x=10, y=77, width=115, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Keelung',
                    area=ImagemapArea(
                        x=125, y=77, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Shilin',
                    area=ImagemapArea(
                        x=230, y=77, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Linkou',
                    area=ImagemapArea(
                        x=335, y=77, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Sanchong',
                    area=ImagemapArea(
                        x=440, y=77, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Xizhi',
                    area=ImagemapArea(
                        x=545, y=77, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Songshan',
                    area=ImagemapArea(
                        x=650, y=77, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Wanhua',
                    area=ImagemapArea(
                        x=755, y=77, width=100, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Xinzhuang',
                    area=ImagemapArea(
                        x=10, y=147, width=115, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Yonghe',
                    area=ImagemapArea(
                        x=125, y=147, width=105, height=70
                    )
                ),
                 MessageImagemapAction(
                    text='+Banqiao',
                    area=ImagemapArea(
                        x=230, y=147, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Taoyuan',
                    area=ImagemapArea(
                        x=335, y=147, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Xindian',
                    area=ImagemapArea(
                        x=440, y=147, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Pingzhen',
                    area=ImagemapArea(
                        x=545, y=147, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Zhongli',
                    area=ImagemapArea(
                        x=650, y=147, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Longtan',
                    area=ImagemapArea(
                        x=755, y=147, width=100, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Hsinchu',
                    area=ImagemapArea(
                        x=10, y=217, width=115, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Zhudong',
                    area=ImagemapArea(
                        x=125, y=217, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Toufen',
                    area=ImagemapArea(
                        x=230, y=217, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Miaoli',
                    area=ImagemapArea(
                        x=335, y=217, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Sanyi',
                    area=ImagemapArea(
                        x=440, y=217, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Fengyuan',
                    area=ImagemapArea(
                        x=545, y=217, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Xitun',
                    area=ImagemapArea(
                        x=650, y=217, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Dali',
                    area=ImagemapArea(
                        x=755, y=217, width=100, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Changhua',
                    area=ImagemapArea(
                        x=10, y=287, width=115, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Puli',
                    area=ImagemapArea(
                        x=125, y=287, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Nantou',
                    area=ImagemapArea(
                        x=230, y=287, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Mailiao',
                    area=ImagemapArea(
                        x=335, y=287, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Taixi',
                    area=ImagemapArea(
                        x=440, y=287, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Xingang',
                    area=ImagemapArea(
                        x=545, y=287, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Puzi',
                    area=ImagemapArea(
                        x=650, y=287, width=105, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Chiayi',
                    area=ImagemapArea(
                        x=755, y=287, width=100, height=70
                    )
                ),
                MessageImagemapAction(
                    text='+Xinying',
                    area=ImagemapArea(
                        x=10, y=357, width=115, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Shanhua',
                    area=ImagemapArea(
                        x=125, y=357, width=105, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Tainan',
                    area=ImagemapArea(
                        x=230, y=357, width=105, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Nanzi',
                    area=ImagemapArea(
                        x=335, y=357, width=105, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Renwu',
                    area=ImagemapArea(
                        x=440, y=357, width=105, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Zuoying',
                    area=ImagemapArea(
                        x=545, y=357, width=105, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Pingtung',
                    area=ImagemapArea(
                        x=650, y=357, width=105, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Fengshan',
                    area=ImagemapArea(
                        x=755, y=357, width=100, height=65
                    )
                ),
                MessageImagemapAction(
                    text='+Qianzhen',
                    area=ImagemapArea(
                        x=0, y=422, width=110, height=55
                    )
                ),
                MessageImagemapAction(
                    text='+Hengchun',
                    area=ImagemapArea(
                        x=125, y=422, width=105, height=55
                    )
                ),
                MessageImagemapAction(
                    text='+Yilan',
                    area=ImagemapArea(
                        x=230, y=422, width=105, height=55
                    )
                ),
                MessageImagemapAction(
                    text='+Hualien',
                    area=ImagemapArea(
                        x=335, y=422, width=105, height=55
                    )
                ),
                MessageImagemapAction(
                    text='+Taitung',
                    area=ImagemapArea(
                        x=440, y=422, width=105, height=55
                    )
                ),
                MessageImagemapAction(
                    text='+Matsu',
                    area=ImagemapArea(
                        x=545, y=422, width=105, height=55
                    )
                ),
                MessageImagemapAction(
                    text='+Kinmen',
                    area=ImagemapArea(
                        x=650, y=422, width=105, height=55
                    )
                ),
                MessageImagemapAction(
                    text='+Magong',
                    area=ImagemapArea(
                        x=755, y=422, width=100, height=55
                    )
                )
            ]
        )
        line_bot_api.reply_message(event.reply_token,imagemap_message)
        return
    
    if event.message.text=="help" or event.message.text=='h' or event.message.text == '?' or event.message.text=='？':
        buttons_template = TemplateSendMessage(
        alt_text='目錄 template',
        template=ButtonsTemplate(
            title="----===黑墨鏡功能列示===----",
            text= "   演示其中4項功能如下:",
            thumbnail_image_url='https://i.imgur.com/jmXjgd9.jpg',
            actions=[
                MessageTemplateAction(label="看今日新聞",text="news"),
                MessageTemplateAction(label="看股價",text="#3481"),
                MessageTemplateAction(label='看臺南空氣品質',text="+Tainan"),
                MessageTemplateAction(label="看臺南天氣",text="weather")
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return
    
    if (len(event.message.text)>1 ) and (event.message.text[0]=='#' or event.message.text[0]=='＃'):
        try:
            stock = twstock.realtime.get(event.message.text[1:])
            msg1 = "-=="+stock['info']['name']+"("+event.message.text[1:]+")==-\n目前價格:"+stock['realtime']['latest_trade_price']
            msg2 = msg1+"\n開盤價:"+stock['realtime']['open']+"\n最高價:"+stock['realtime']['high']+"\n最低價:"+stock['realtime']['low']
            msg3 = msg2+"\n累積成交量:"+stock['realtime']['accumulate_trade_volume']+"\n\n買入建議: "
            
            stk = Stock(event.message.text[1:])
            bfp = BestFourPoint(stk)
            rs = bfp.best_four_point()
            print(rs)
            if rs[0]:
                msg4="有,"+rs[1]
            else:
                msg4="無"
            
            print(msg4)
            reply_msg.text = msg3+msg4
        except:
            reply_msg.text = "錯誤"
        
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
        
     
    if event.message.text[0]=='$' or event.message.text[0]=='＄':
        expr = FullToHalf(event.message.text[1:])
        reply_msg.text = str(eval(expr))
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
    
    if event.message.text == "c$" or event.message.text=="c＄":
        dfs = pandas.read_html('http://rate.bot.com.tw/xrt?Lang=zh-TW')
        currency = dfs[0]
        currency = currency.ix[:,0:5]
        currency.columns = [u'幣別', u'現-買', u'現-賣', u'即-買', u'即-賣']
        currency[u'幣別'] = currency[u'幣別'].str.extract('\((\w+)\)', expand=True)
        #currency['Date'] = datetime.now().strftime('%Y-%m-%d')
        #currency['Date'] = pandas.to_datetime(currency['Date'])
        reply_msg.text = currency.to_string()
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
    
    if event.message.text[0]=='+':
        locationStr = requests.get('https://taqm.epa.gov.tw/taqm/aqs.ashx?lang=tw&act=aqi-epa&ts=' + str(time.time()))
        locations = json.loads(locationStr.text)
        places = event.message.text[1:]
   
        for location in locations['Data']:
            if location['SiteKey'] == places:
                msg = "  --==("+location['SiteName']+")空氣品質==--\n"+location['Address']+"\n時間 : "+location['Time']
                msg += "\n\n主要汙染源 : "+location['MainPollutant']+"\nAQI-->"+location['AQI']+"\nPM2.5-->"+location['PM25']
                msg += "\nPM10-->"+location['PM10']+"\nCO-->"+location['CO']+"\nNO2-->"+location['NO2']+"\nO3-->"+location['O3']
                msg += "\nSO2-->"+location['SO2']
        
        reply_msg.text = msg
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return
    
    if event.message.text[0]=='!' or event.message.text[0]=='！':
        pp,ii = getSticker()
        line_bot_api.reply_message(event.reply_token,StickerSendMessage(package_id=pp, sticker_id=ii))
        return
    
    if event.message.text =='a' or event.message.text == 'A':
        cnt, data = query_sentence()
        if cnt != 0:
            print(data)
            reply_msg.text = data[1]
            line_bot_api.reply_message(event.reply_token,reply_msg)
            return
    
    if event.message.text[0]=='&' or event.message.text[0]=='＆':
        locationStr = requests.get('https://taqm.epa.gov.tw/taqm/aqs.ashx?lang=tw&act=aqi-epa&ts=' + str(time.time()))
        locations = json.loads(locationStr.text)
        places = ['FugueiCape','Yangming','Tamsui','Shilin','Linkou','Zhongshan','Songshan','Xinzhuang','Yonghe','Banqiao','Pingzhen','Hsinchu','Fengyuan','Changhua','Mailiao','Chiayi','Tainan','Shanhua','Renwu','Zuoying','Xiaogang','Yilan','Hualien']
        msg="-==空氣品質==-\n"
        amsg=""
        for location in locations['Data']:
            if location['SiteKey'] in places:
                amsg += location['SiteName']+",[AQI:{:>4s}".format(location['AQI'])+"],[PM2.5:{:>4s}".format(location['PM25'])+"]\n"
                atime = location['Time']
        
        msg = msg+"資料時間:"+atime+"\n"+amsg
        reply_msg.text = msg
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return
    
    if event.message.text == "文字":
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=event.message.text))
        return
    elif event.message.text == "圖片" or event.message.text == "image" or event.message.text == 'i':
        line_bot_api.reply_message(event.reply_token,ImageSendMessage(original_content_url='https://i.imgur.com/4q4uvMl.jpg', preview_image_url='https://i.imgur.com/UE72vxR.jpg'))
        return
    elif event.message.text == "影片":
        line_bot_api.reply_message(event.reply_token,VideoSendMessage(original_content_url='影片網址', preview_image_url='預覽圖片網址'))
        return
    elif event.message.text == "音訊":
        line_bot_api.reply_message(event.reply_token,AudioSendMessage(original_content_url='音訊網址', duration=100000))
        return
    
    if event.message.text[0:2] == "t+":
        ss1 = FullToHalf(event.message.text[2:])
        ss2 = ss1.split(':')
        print(ss1)
        key = ss2[0]
        value = ss2[1]
        #print("key:%s,value:%s,user:%s,time:%s",(key,value,event.source.user_id,event.timestamp))
        cnt,data = query_how(key)
        
        if cnt != 0 :
            update_how(key,value,event.source.user_id,event.timestamp)
        else:
            insert_how(key,value,event.source.user_id,event.timestamp)
        
        reply_msg.text = "感謝你的教導,我已經會了呦!"
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return
    
    if event.message.text[0:2] == "t-":
        cnt, data = query_how(event.message.text[2:])
        if cnt!= 0:
            delete_how(event.message.text[2:])
            msg = "腦袋中的這個規則,已刪除..."
        else:
            msg = "腦袋中沒有這個,不用刪"
        
        reply_msg.text = msg
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return
    
    if event.message.text == "%offtrans":
        if event.source.type == "user":
            turnoff_trans(event.source.user_id)
        
        if event.source.type == "group":
            turnoff_trans(event.source.group_id)
            
        reply_msg.text = "已關閉翻譯功能!"
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return
    
    if event.message.text == "%ontrans":
        if event.source.type == "user":
            turnon_trans(event.source.user_id)
        
        if event.source.type == "group":
            turnon_trans(event.source.group_id)
        
        reply_msg.text = "已開啟翻譯功能!"
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return           
        
    if event.message.text[0:5] == "email":
        mail_settings = {
            "MAIL_SERVER": 'smtp.gmail.com',
            "MAIL_PORT": 465,
            "MAIL_USE_TLS": False,
            "MAIL_USE_SSL": True,
            "MAIL_USERNAME": os.environ['EMAIL_USER'],
            "MAIL_PASSWORD": os.environ['EMAIL_PASSWORD']
        }
        app.config.update(mail_settings)
        mail = Mail(app)
        
        msg = Message(subject="linebot send message here!",
                      sender=app.config.get("MAIL_USERNAME"),
                      recipients=["hungtai.chen@gmail.com"], # replace with your email for testing
                      body=event.message.text[6:])
        mail.send(msg)
        reply_msg.text = "感謝你的意見,已經反應給作者了."
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return
    
    if (len(event.message.text) > 1) and (event.message.text[0]=='@' or event.message.text[0]=='＠'):
        cname=event.message.text[1:]
        b = twstock.codes
       
        result=[]
        result=[key for key, val in b.items() if cname in val]
        if result != [] :
            msg= ",".join(result)
            msg0 = cname+"的股票代碼為:"+msg+"\n"
        else:
            msg="錯誤"
            msg0 = cname+"的股票代碼為:"+msg+"\n"
        
        id = str(msg)
        try:
            stock = twstock.realtime.get(id)
            msg1 = "-=="+stock['info']['name']+"("+ id +")==-\n目前價格:"+stock['realtime']['latest_trade_price']
            msg2 = msg1+"\n開盤價:"+stock['realtime']['open']+"\n最高價:"+stock['realtime']['high']+"\n最低價:"+stock['realtime']['low']
            msg3 = msg2+"\n累積成交量:"+stock['realtime']['accumulate_trade_volume']+"\n\n買入建議: "
                      
            stk = Stock(id)
            bfp = BestFourPoint(stk)
            rs = bfp.best_four_point()
            print(rs)
            if rs[0]:
                msg4="有,"+rs[1]
            else:
                msg4="無"
            
            print(msg4)
            reply_msg.text = msg0+msg3+msg4
        except:
            reply_msg.text = "錯誤"
        
        line_bot_api.reply_message(event.reply_token, reply_msg)
        print(reply_msg)
        return
       
  
    #dic = Dict()
    #dic.in_String = event.message.text
    #resp = dic.translate()
    
    cnt,data = query_how(event.message.text)
    if cnt != 0:
        print(data)
        reply_msg.text = data[1]
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
    
    #rep = get_Qna_answer(event.message.text)
    #if rep != "Error":
    #    reply_msg.text = rep
    #    line_bot_api.reply_message(event.reply_token,reply_msg)
    #    return
    
    #if (data[0] == 'N'):
    #    resp = youdao_translate(event.message.text)
    #    outtext = resp['translateResult'][0][0]['tgt']
    
    #    reply_msg.text = outtext
    #    print(reply_msg)
    #    line_bot_api.reply_message(event.reply_token,reply_msg)
    #    return
 
    a = event.source
    print(a)
    
    if event.source.type == "user":
        num,data = query_config(a.user_id)
        if num ==0:
            insert_config_N(a.user_id)
            return
    
    if event.source.type == "group":
        num, data = query_config(a.group_id)
        if num ==0:
            insert_config_N(a.group_id)
            return
        
    if (data[0] == 'N'):
        translate_client = translate.Client()
        in_txt = event.message.text
        target = 'en'
        out_txt = translate_client.translate(in_txt,target_language=target)
        
        print(out_txt)
        
        if out_txt['detectedSourceLanguage'] == 'en':
            target = 'zh-TW'
            out_txt = translate_client.translate(in_txt,target_language=target)
        
        out_string = out_txt['translatedText'].replace('&#39;','\'')
        reply_msg.text = out_string.replace('&quot;','\"') 
        line_bot_api.reply_message(event.reply_token,reply_msg)
        return
    
    
    return

    """
    gs = goslate.Goslate()
    #text = translator.translate(event.message.text,src='zh-TW',dest='en').text
    #eng_detect = translator.detect('中文')
    
    try:
    #    eng_trans = translator.translate(event.message.text,src='zh-TW',dest='en').text
        eng_trans = gs.translate(event.message.text,'en')
    except:
        eng_trans = "Error!"
    
    try:
    #    jap_trans = translator.translate(event.message.text,src='zh-TW',dest='jp').text
        jap_trans = gs.translate(event.message.text,'ja')
    except:
        jap_trans = "Error!"
        
    try:
    #    ko_trans = translator.translate(event.message.text,src='zh-TW',dest='ko').text
        ko_trans = gs.translate(event.message.text,'ko')
    except:
       ko_trans = "Error!"
        
    try:
    #    de_trans = translator.translate(event.message.text,src='zh-TW',dest='de').text
        de_trans = gs.translate(event.message.text,'de')
    except:
        de_trans = "Error!"
        
    #reply_msg.text = "英文翻譯=>" + eng_trans + "\n\n日文翻譯=>" + jap_trans + "\n\n韓文翻譯=>" + ko_trans + "\n\n德文翻譯=>" + de_trans
    
    reply_msg.text =  "原:"+ event.message.text +"\n\n英文=>" + eng_trans+"\n\n日文=>" + jap_trans+"\n\n韓文=>" + ko_trans+"\n\n德文=>" + de_trans
    
    
   
    try:
        reply_msg.text = "英文翻譯=>" + translator.translate(event.message.text,src='zh-TW',dest='en').text +"\n日文翻譯=>" + translator.translate(event.message.text,src='zh-TW',dest='ja').text
        
        #+ "\n韓文翻譯=>" + translator.translate(event.message.text,src='zh-TW',dest='ko').text
        
        #tr_text = translate_text(event.message.text)
        #reply_msg.text = '你:' + event.message.text + "==>" + tr_text
    except:
        reply_msg.text = "Google Blocking...=>請再次複製貼上試試!!"
    """
    

    
    
      
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
