#!/usr/bin/env python

import sys
import os
import aiohttp
import asyncio
import html5lib
from bs4 import BeautifulSoup


headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36'}
provinces = [['河北省', '石家庄市'], ['山西省', '太原市'], ['辽宁省', '沈阳市'], ['吉林省', '长春市'], ['黑龙江省', '哈尔滨市'], ['江苏省', '南京市'], ['浙江省', '杭州市'], ['安徽省', '合肥市'], ['福建省', '福州市'], ['江西省', '南昌市'], ['山东省', '济南市'], ['河南省', '郑州市'], ['广东省', '广州市'], ['湖南省', '长沙市'], ['湖北省', '武汉市'], ['海南省', '海口市'], ['四川省', '成都市'], ['贵州省', '贵阳市'], ['云南省', '昆明市'], ['陕西省', '西安市'], ['甘肃省', '兰州市'], ['青海省', '西宁市'], ['内蒙古自治区', '呼和浩特市'], ['广西壮族自治区', '南宁市'], ['西藏自治区', '拉萨市'], ['宁夏回族自治区', '银川市'], ['新疆维吾尔自治区', '乌鲁木齐市']]


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


async def load_city_old(province, url):
    html = ''
    async with aiohttp.ClientSession(headers=headers) as session:
        html = await fetch(session,  url)
    soup = BeautifulSoup(html, 'html5lib')
    cities = []
    for table in soup.find_all('table', class_='t12'):
        for tr in table.find_all('tr'):
            if tr.find('b'):
                tds = tr.find_all('td')
                if len(tds) != 4:
                    continue
                cities.append({'province': province, 'city': tds[0].text, 'code': tds[2].text})
                print(province, tds[0].text, tds[2].text)
#    for info in provinces:
#        if info[0] == province:
#            ccode = None
#            for info1 in cities:
#                if info[1] == info1['city']:
#                    ccode = info1['code']
#                    break
#            for info1 in cities:
#                print(info1['province'], info1['city'], '86'+ccode.lstrip('0')+info1['code'].lstrip('0'))


async def load_province_old():
    html = ''
    async with aiohttp.ClientSession(headers=headers) as session:
        html = await fetch(session, 'http://www.ip138.com/post/')
    soup = BeautifulSoup(html, 'html5lib')
    for div in soup.find_all('div'):
        if div.get('id', None) == 'quanguo':
            for tr in div.table:
                if tr and hasattr(tr, 'td'):
                    for content in tr.find_all('a'):
                        if content.name == 'a':
                            href = content.get('href', '')
                            if href:
                                await load_city(content.text, 'http://www.ip138.com'+href)
                                await asyncio.sleep(0.5)


async def load_city(province, url):
    html = ''
    async with aiohttp.ClientSession(headers=headers) as session:
        html = await fetch(session,  url)
    soup = BeautifulSoup(html, 'html5lib')
    cities = []
    for table in soup.find_all('table', class_='table'):
        for tr in table.find_all('tr'):
            if tr.find('b'):
                tds = tr.find_all('td')
                if len(tds) != 4:
                    continue
                cities.append({'province': province, 'city': tds[0].text, 'code': tds[2].text})
                print(province, tds[0].text, tds[2].text)
#    for info in provinces:
#        if info[0] == province:
#            ccode = None
#            for info1 in cities:
#                if info[1] == info1['city']:
#                    ccode = info1['code']
#                    break
#            for info1 in cities:
#                print(info1['province'], info1['city'], '86'+ccode.lstrip('0')+info1['code'].lstrip('0'))


async def load_province():
    html = ''
    async with aiohttp.ClientSession(headers=headers) as session:
        html = await fetch(session, 'http://www.ip138.com/post/')
    soup = BeautifulSoup(html, 'html5lib')
    for table in soup.find_all('table'):
        if table.get('id', None) == 'quanguo':
            for tr in table:
                if tr and hasattr(tr, 'td'):
                    for content in tr.find_all('a'):
                        href = content.get('href', '')
                        if href:
                            await load_city(content.text, 'http://www.ip138.com'+href)
                            await asyncio.sleep(0.5)


async def main():
    await load_province()
    # await load_city('', '')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print('exit')


