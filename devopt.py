#!/usr/bin/env python3

import sys
import os
import logging
import json
import time
import hashlib
import re
from aiohttp import web, http, ClientSession
http.SERVER_SOFTWARE = "devopt/1.0"
from subprocess import Popen, PIPE, check_output
from argparse import ArgumentParser
import psutil

logkeys = {
    'level': logging.DEBUG,
    'filename': 'app.log',
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
    'datefmt': '%Y-%m-%d %H:%M:%S'
}

logging.basicConfig(**logkeys)


def NetcardInfo():
    ips = []
    ifaddrs = psutil.net_if_addrs()
    for k, v in ifaddrs.items():
        for item in v:
            if str(item.family) == 'AddressFamily.AF_INET':
                ips.append(item.address)
    return ','.join(ips)


def SystemUUID():
    exp = re.compile('uuid:(?P<uuid>.*)', re.IGNORECASE)
    output = check_output(['/usr/sbin/dmidecode', '-t', 'system']).decode()
    for line in output.split('\n'):
        m = exp.search(line)
        if m and m.groupdict():
            uuid = m.groupdict().get('uuid', '').strip()
            return uuid
    return None


async def JsonPost(url, data=None):
    try:
        async with ClientSession() as session:
            async with session.post(url, data) as response:
                content = await response.text()
                return json.loads(content)
    except:
        logging(sys.exc_info())
    return {}

class HeaderFilter:
    def __init__(self):
        self.headers_ = {}

    def register(self, name, *values):
        matched = self.headers_.get(name)
        if matched is None:
            matched = values
        else:
            matched += values
        self.headers_[name] = matched

    def match(self, request, matched_all = True):
        matches = 0
        for name, values in self.headers_.items():
            for header in request.headers.getall(name, []):
                matched = False
                for value in values:
                    matched = (value in header)
                    if matched:
                        break
                if matched:
                    matches += 1
                    break
        if ((matches > 0 and not matched_all) or (matches == len(self.headers_) and matched_all)):
            return True
        return False

headers_filter = HeaderFilter()
headers_filter.register('Content-Type', 'application/json')

async def RequestFilter(app, handler):
    async def Handler(request, *args, **kwargs):
        if not headers_filter.match(request):
            return web.HTTPBadRequest()
        return await handler(request, *args, **kwargs)
    return Handler

middlewares = [
    RequestFilter
]

class DevOptApplication:
    def __init__(self):
        self.newpass_ = ''
        self.app_ = web.Application(middlewares=middlewares)
        self.app_.router.add_post('/devopt/passwd/prepare', self.PreparePassword)
        self.app_.router.add_post('/devopt/passwd/submit', self.SubmitPassword)

    def HashPassword(self, key, salt='', rounds=20):
        m = hashlib.md5()
        if rounds == 1:
            m.update((key+salt).encode())
            return m.hexdigest()
        else:
            m.update(self.HashPassword(key, salt, rounds-1).encode())
            return m.hexdigest()

    def NewPassword(self, salt, rounds=20):
        timestamp = str(time.time()).split('.')[0]
        return self.HashPassword(timestamp, salt)

    def SetPassword(self, username, password):
        with Popen(['/usr/bin/passwd', username], stdin=PIPE) as p:
            newpass = (password + '\n').encode('ascii')
            p.stdin.write(newpass)
            p.stdin.write(newpass)

    async def PreparePassword(self, request):
        body = await request.text()
        logging.info(body)
        try:
            data = json.loads(body)
            username = data.get('username', None)
            opkey = data.get('opkey', None)
            if not username or not opkey:
                logging.error('prepare password failed: ' + body)
                return web.json_response({'status': 'failed'})
            self.newpass_ = self.NewPassword(opkey)
            return web.json_response({'status': 'ok', 'newpass': self.newpass_, 'net': NetcardInfo(), 'uuid': SystemUUID()})
        except:
            self.newpass_ = ''
            logging.error(sys.exc_info())
            return web.json_response({'status': 'failed'}, status=500)

    async def SubmitPassword(self, request):
        body = await request.text()
        logging.info(body)
        try:
            data = json.loads(body)
            username = data.get('username', None)
            opkey = data.get('opkey', None)
            newpass = data.get('newpass')
            if not username or not opkey or (self.newpass_ != newpass):
                logging.error('submit password failed: ' + body)
                return web.json_response({'status': 'failed'})
            self.SetPassword(username, newpass)
            return web.json_response({'status': 'ok'})
        except:
            logging.error(sys.exc_info())
            return web.json_response({'status': 'failed'}, status=500)

    def Start(self, argv):
        parser = ArgumentParser(prog='devpot')
        parser.add_argument('--host', dest='host', default='127.0.0.1')
        parser.add_argument('--port', dest='port', default='2020')
        args = parser.parse_args(argv)
        host, port = args.host, args.port
        web.run_app(self.app_, host=host, port=port)


if __name__ == '__main__':
    pid = os.fork()
    if pid != 0:
        sys.exit(0)
    app = DevOptApplication()
    app.Start(sys.argv[1:])
