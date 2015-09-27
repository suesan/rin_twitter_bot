# -*- coding: utf-8 -*-
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
from bs4 import BeautifulSoup
import re
from datetime import datetime
from datetime import timedelta, tzinfo
from calendar import monthrange
import locale
import time
import requests as req
from requests_oauthlib import OAuth1
import json
import urllib

class JST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=9)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return 'JST'

class Rin:
    base_url        = 'http://www.rinkikurin.com/'
    reservation_uri = 'ご予約'
    response_url    = base_url + urllib2.quote(reservation_uri)
    next_manth_uri  = '?ymd='
    next_url        = ''

    consumer_key        = 'Twitter consumer keyをいれる'
    consumer_secret     = 'Twitter consumer secret keyをいれる'
    access_token_key    = 'Twitter access token keyをいれる'
    access_token_secret = 'Twitter access token secret keyを入れる'

    @classmethod
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

    @classmethod
    def isLastDate(self, date):
        """ 月末か判定する

        Args:
            datetime
        Returns:
            True:月末の場合
            False:上記以外
        """

        weeks, day = monthrange(date.year, date.month)
        if (date.strftime('%d') == str(day)):
            return True
        else:
            return False

    @classmethod
    def getTodayInfo(self):
        """ 今日の予約のURLを取得する関数

        Args:
            none

        Returns:
            url(今日の予約URL)
        """

        # 予約ページからContent-Bodyを取得する
        response = urllib2.urlopen(Rin.response_url)
        body = response.read()

        # HTML をパースする
        soup = BeautifulSoup(body, 'html.parser')

        # classにtodayが入っているものを今日の予約日と判断する
        td_today = soup.find('td', {'class': re.compile('today')})
        # <a>タグを取り出す
        today_link = td_today.a
        today_url  = today_link['href']
        day_info   = td_today.a.text

        return (day_info, today_url)

    @classmethod
    def getReserveInfo(self, url):

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
            # day-calendarが存在しない場合、定休日とみなす
            return (u'ー', state_list, dt_str)


        dayly_condition = ''
        pattern = r'\d\d:30'
        for cal in div_day_calendar:
            dayly_condition = cal.find('p').text + u' の予約状況'
            tr_list = cal.find_all('tr')
            for tr in tr_list:
                if (u'時間' == tr.find('th', {'class': 'day-left'}).text):
                    continue

                time = tr.find('th', {'class': 'day-left'}).text
                try:
                    if (re.match(pattern, str(time))):
                        continue
                except re.error:
                    pass

                state = tr.find('td', {'class': 'day-right'}).text
                if (not state == u'－'):
                    state_list.append(u'{0} {1}'.format(time, state))

        return (dayly_condition, state_list, dt_str)

    @classmethod
    def getNextDayInteger(self, date):
        d = date + timedelta(days=2)
        s = '{0}{1}{2}'.format(d.year, d.month, d.day)
        int_time = int(time.mktime(datetime.strptime(s, '%Y%m%d').timetuple()))
        return int_time

    @classmethod
    def generateShortURL(self, url):
        longUrl      = url
        base_url = 'https://api-ssl.bitly.com/v3/shorten?access_token=(Your bitly token)&longUrl='
        f = urllib2.urlopen(base_url + longUrl)
        return json.load(f)[u'data'][u'url']

    @classmethod
    def createMessage(self, dayly_condition, list, url):
        message = dayly_condition + '\n'
        for item in list:
            message += item + '\n'
        message += url + ' \n'
        message += u'#凛 #Rin #治療院'
        return message

    @classmethod
    def twitterPost(self, message):

        tweet_url = 'https://api.twitter.com/1.1/statuses/update.json'
        auth = OAuth1(Rin.consumer_key,
            Rin.consumer_secret,
            Rin.access_token_key,
            Rin.access_token_secret)
        params = {'status': message}
        res = req.post(tweet_url, params = params, auth = auth)

# 現在時刻の取得
date = datetime.now(tz=JST())

message = ''
if (Rin.isCloseBusiness(date)):
    # 営業時間内の場合
    day_info, url = Rin.getTodayInfo()
    if ((day_info == u"○") or (day_info == u"△") or (day_info == u"×")):
        (dayly_condition, list, dt_str) = Rin.getReserveInfo(url)
        if (dayly_condition == u'ー'):
            # 営業時間内は手前で除外されているため、ここには入らないはず

            message = u'{0}は定休日です'.format(dt_str)
        else:
            url = Rin.generateShortURL(url)
            message = Rin.createMessage(dayly_condition, list, url)
    else:
        # 同一メッセージは連続して投げれない
        message = u'本日は定休日です'
else:
    # 営業時間外の場合
    if (not Rin.isLastDate(date)):
        # 月末ではない場合
        nextdate_int = Rin.getNextDayInteger(date)
        url = Rin.response_url + Rin.next_manth_uri + str(nextdate_int)
        url = Rin.generateShortURL(url)
        (dayly_condition, list) = Rin.getReserveInfo(url)
        if (dayly_condition == u'ー'):
            message = u'{0}は定休日です'.format(dt_str)
        else:
            message = Rin.createMessage(dayly_condition, list, url)

# Twitterにポストする
Rin.twitterPost(message)

