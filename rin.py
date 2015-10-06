# -*- coding: utf-8 -*-
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
import json
import locale
import random
import re
import requests as req
import time
from bs4 import BeautifulSoup
from datetime import datetime
from datetime import timedelta
from datetime import tzinfo
from calendar import monthrange
from configparser import SafeConfigParser
from requests_oauthlib import OAuth1

class JST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=9)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return 'JST'

class TwitterClass():
    consumer_key        = ''
    consumer_secret     = ''
    access_token        = ''
    access_token_secret = ''
    auth = None

    """docstring for """
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
        #super(, self).__init__()
        self.consumer_key        = consumer_key
        self.consumer_secret     = consumer_secret
        self.access_token        = access_token
        self.access_token_secret = access_token_secret
        self.auth = OAuth1(
            self.consumer_key,
            client_secret         = self.consumer_secret,
            resource_owner_key    = self.access_token,
            resource_owner_secret = self.access_token_secret
        )

    def twitter_update(self, message):
        url = u'https://api.twitter.com/1.1/statuses/update.json'
        data = {
            'status': message
        }
        response = req.post(url, data=data, auth=self.auth)
        if response.status_code != 200:
            print(u'Error code: %d' %(response.status_code))
        print(json.loads(response.text))

class BitlyClass(object):
    """docstring for """
    def shorten(self, target_url):
        self.url          = u'https://api-ssl.bitly.com/v3/shorten?access_token='
        self.bity_api_key = u'ビットリーAPIキー'
        self.target_url   = target_url
        self.long_url     = u'&longUrl='
        self.api_shorten  = self.url + self.bity_api_key + self.long_url + self.target_url
        response = urllib2.urlopen(self.api_shorten)
        return json.load(response)[u'data'][u'url']

class RinClass(object):
    def __init__(self):
        self.url             = u'http://www.rinkikurin.com/'
        self.reservation_uri = u'ご予約'
        self.response_url    = self.url + urllib2.quote(self.reservation_uri.encode("utf-8"))
        self.next_manth_uri  = u'?ymd='
        self.next_url        = ''
        self.is_holiday      = 0;
        self.is_reserve      = 0; # 0 : 空き時間なし / 1：空き時間あり
        self.tag             = u'#凛 #治療院 '
        self.tags            = [u'#凛', u'#治療院', u'#小平', u'#東村山市', u'#小平駅南口', u'#徒歩３分', u'#鍼灸', u'#健康', u'#肩こり']
        self.BodyCare_Rin    = u'@BodyCare_Rin'

    def isCloseBusiness(self, date):
        """ 営業時間に間に合うか判定する(18時30分)

        Args:
            date(today)
        Returns:
            True: 18:30以内の場合
            False: 上記以外
        """

        hour = date.strftime('%H%M')
        if (1830 >= int(hour)):
            return True
        else:
            return False

    def getTodayInfo(self):
        """ 今日の予約のURLを取得する関数

        Args:
            none

        Returns:
            day_info:
                混雑状況
            url:
                今日の予約URL
        """

        # 予約ページからContent-Bodyを取得する
        response = urllib2.urlopen(self.response_url)
        body     = response.read()

        # HTML をパースする
        soup = BeautifulSoup(body, 'html.parser')

        # classにtodayが入っているものを今日の予約日と判断する
        td_today = soup.find('td', {'class': re.compile('today')})
        # calendar-markの値が－だったら、休暇日
        day_info = td_today.find('div', {'class': re.compile('calendar-mark')})
        if (u"－" == day_info.text):
            return (day_info, None)

        # <a>タグを取り出す
        today_link = td_today.a
        today_url  = today_link['href']
        day_info   = td_today.a.text

        return (day_info, today_url)

    def getReserveInfo(self, url):
        """予約ページを解析する

        Args:
            url:
                予約ページのURL
        Returns:
            daily_condition:
                予約状況
            state_list:
                予約状況一覧
            dt_str:
                予約対象ページの日
        """

        date_integer = url.split('=')[1]
        dt           = datetime.fromtimestamp(int(date_integer))
        weekly       = ["月","火","水","木","金","土","日"]
        dt_str       = dt.strftime('%Y年%m月%d日') +'({0}) '.format(weekly[dt.weekday()])

        response         = urllib2.urlopen(url)
        body             = response.read()
        soup             = BeautifulSoup(body, 'html.parser')
        div_day_calendar = soup.find_all('div', {'class': 'day-calendar'})

        state_list = []
        if (len(div_day_calendar) == 0):
            # ページ内にday-calendarが存在しない場合、定休日とみなす
            self.is_holiday = 1
            return (u'ー', state_list, dt_str)

        daily_condition = ''
        pattern = r'\d\d:30'
        for cal in div_day_calendar:
            daily_condition = cal.find('p').text + u' の予約状況'
            tr_list = cal.find_all('tr')
            for tr in tr_list:
                if (u'時間' == tr.find('th', {'class': 'day-left'}).text):
                    continue

                # 時間を取得する
                time = tr.find('th', {'class': 'day-left'}).text
                try:
                    if (re.match(pattern, str(time))):
                        # 30分は無視する

                        continue
                except re.error:
                    pass

                # 予約状況を取得する
                state = tr.find('td', {'class': 'day-right'}).text
                if (state == u'○'):
                    self.is_reserve = 1

                if (not state == u'－'):
                    state_list.append(u'{0} {1}'.format(time, state))

        return (daily_condition, state_list, dt_str)

    def getNextDayInteger(self, date, days):
        """指定日付をInteger型で生成する

        Args:
            date:
                ベースとなる日付
            days:
                進めたい日数(1日すすめる場合、2を指定)
        Returns:
            Integer型の時間
        """
        dt       = date + timedelta(days = days)
        dts      = '{0}{1}{2}'.format(dt.year, dt.month, dt.day)
        int_time = int(time.mktime(datetime.strptime(dts, '%Y%m%d').timetuple()))
        return int_time

    def createMessage(self, resrve_date, list, url):
        """Tweetするメッセージを生成する

        Args:
            resrve_date:
                予約日時
            list:
                時間毎の状況
            url:
                予約ページのURL
        Returns:
            生成したメッセージ
        """
        message = resrve_date + '\n'
        for item in list:
            message += item + '\n'
        message += url + ' \n'
        message += self.tag
        if (self.is_reserve == 1):
            message += u' #空きあり'
        return message

if __name__ == '__main__':
    # 現在時刻(日本時間)
    date = datetime.now(tz=JST())

    rin   = RinClass()
    bitly = BitlyClass()

    message = None
    if (rin.isCloseBusiness(date)):
        # 営業時間内の場合
        day_info, url = rin.getTodayInfo()
        if day_info in [u'○', u'△', u'×']:
            # 営業時間の場合

            (daily_condition, list, dt_str) = rin.getReserveInfo(url)
            if (rin.is_reserve == 0):
                # 受付終了の場合

                message = u'本日の予約受付は終了しました\nありがとうございました\n{0}\n{1}'.format(bitly.shorten(rin.url), rin.tag)
            else:
                if (daily_condition == u'ー'):
                    # 営業時間内は手前で除外されているため、ここには入らないはず

                    message = u'{0}は定休日です\n{1}\n{2}'.format(dt_str, bitly.shorten(rin.url), rin.tag)
                else:
                    url = bitly.shorten(url)
                    message = rin.createMessage(daily_condition, list, url)
        else:

            random.shuffle(rin.tags)
            tag = u'{0} {1} {2}'.format(rin.tags[0], rin.tags[1], rin.tags[2])

            # 同一メッセージは連続して投げれない(Twittershot仕様)
            message = u'本日は定休日です\n{0}\n{1}'.format(bitly.shorten(rin.url), tag)
    else:
        # 営業時間外の場合

            # 予約のページ表示パラメータ用の日付(integer)生成
            nextdate_int = rin.getNextDayInteger(date, 2)
            # 予約ページの生成
            url = rin.response_url + rin.next_manth_uri + str(nextdate_int)
            # 短縮URLの生成
            short_url = bitly.shorten(url)
            (daily_condition, list, dt_str) = rin.getReserveInfo(url)
            if (daily_condition == u'ー'):
                message = u'{0}は定休日です\n{1}\n{2}'.format(dt_str, bitly.shorten(rin.url), rin.tag)
            else:
                message = rin.createMessage(daily_condition, list, short_url)

    tw = TwitterClass(
        u'consumer_key',
        u'consumer_secret',
        u'access_token',
        u'access_token_secret'
    )
    tw.twitter_update(message)
