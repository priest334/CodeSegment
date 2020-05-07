#! /usr/bin/env python

import sys
import asyncio
import aiohttp
import json
import time
import random
import logging
from string import Template

logging.basicConfig(filename='exception.txt', level=logging.DEBUG)


sqlt = Template("insert into phone_area_tb (phone_prefix,province,city,pa_name,area_id) values ('$prefix','$prov','$city','$prov$city$corp','$code') on conflict(phone_prefix) do update set area_id='$code',province='$prov',city='$city',pa_name='$prov$city$corp';")
sqltnp = Template("insert into phone_area_tb (phone_prefix,province,city,pa_name,area_id) values ('$prefix','$city','$city','$city$corp','$code') on conflict(phone_prefix) do update set area_id='$code',province='$city',city='$city',pa_name='$city$corp';")


class AreaCode:
    def __init__(self):
        pcodes = {}
        with open('capital.txt', encoding='utf8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                name, xcode = line.split(',')
                pcodes.update({name: xcode})
        self._cities = {}
        with open('cities.txt', encoding='utf8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                prov, city, code = line.split(' ')
                d = self._cities.get(prov, {})
                for (name, xcode) in pcodes.items():
                    if prov.startswith(name):
                        code = xcode+code.lstrip('0')
                        break
                d.update({city: code})
                self._cities.update({prov: d})

    def Get(self, province, city):
        for (prov, cities) in self._cities.items():
            if prov.startswith(province):
                for (city_, code) in cities.items():
                    if city_.startswith(city):
                        return code
                break
        return None


area_code = AreaCode()


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


async def location(mobile):
    global area_code
    #url = f"http://mobsec-dianhua.baidu.com/dianhua_api/open/location?tel={mobile}"
    url = f"http://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?resource_name=guishudi&query={mobile}{random.randrange(10000):04d}&_={int(time.time()*1000)}"
    async with aiohttp.ClientSession() as session:
        response = await fetch(session, url)
        if response:
            try:
                data = json.loads(response).get('data', None)
                if data and isinstance(data, (list, tuple)):
                    city = data[0].get('city', '')
                    prov = data[0].get('prov', '')
                    corp = data[0].get('type', '')
                    prefix = data[0].get('key', '')
                    #corp = corp.replace('中国', '')
                    code = area_code.Get(prov if prov else city, city)
                    if prov:
                        return sqlt.substitute(prefix=prefix, city=city, prov=prov, corp=corp, code=code)
                    else:
                        return sqltnp.substitute(prefix=prefix, city=city, corp=corp, code=code)
            except Exception as e:
                logging.warning(e)
    return ''


async def main(argv):
    all_isp_numbers = [
        134, 135, 136, 137, 138, 139, 147, 150, 151, 152, 157, 158, 159, 172, 178, 182, 183, 184, 187, 188, 197, 198,
        130, 131, 132, 145, 155, 156, 166, 171, 175, 176, 185, 186, 196,
        133, 149, 153, 173, 177, 180, 181, 189, 190, 199,
        170, 192
    ]

    file = 'location.txt'
    if len(argv) > 1:
        file = argv[1]

    all_isp_numbers.sort()
    unknown = open("unknown.txt", "a+t")
    with open(file, 'a+t', encoding='gbk') as f:
        for number in all_isp_numbers:
            for i in range(10000):
                prefix = f"{number}{i:04d}"
                line = await location(prefix)
                if line:
                    f.write(line+'\n')
                else:
                    unknown.write(prefix+'\n')
    unknown.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(sys.argv[1:]))
