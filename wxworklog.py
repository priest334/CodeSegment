#!/usr/bin/env python

import sys
import os
import binascii
import struct
from datetime import datetime


def strict_read_lines(content, endline=b'\r\n'):
    oft, size = 0, len(content)
    while oft < size:
        nb = struct.unpack('I', content[oft:oft+4])[0]
        oft += 4
        if nb > (size-oft):
            nb = size-oft
        data = struct.unpack(f'{nb}s', content[oft:oft+nb])[0]
        oft += nb
        while oft < size:
            crlf = struct.unpack('2s', content[oft:oft + 2])[0]
            if crlf == endline:
                break
            data += content[oft:oft+1]
            oft += 1
        oft += 2
        line = bytes((x ^ data[0]) for x in data[1:])
        yield line


def compat_read_lines(content, endline=b'\r\n'):
    oft, size = 0, len(content)
    while oft < size:
        nb = struct.unpack('I', content[oft:oft+4])[0]
        oft += 4
        if nb > (size-oft):
            nb = size-oft
        data = struct.unpack(f'{nb}s', content[oft:oft+nb])[0]
        oft += nb
        if endline is None:
            line = bytes((x ^ data[0]) for x in data[1:])
            yield line
            return
        while oft < size:
            crlf = struct.unpack('2s', content[oft:oft + 2])[0]
            if crlf == endline:
                break
            data += content[oft:oft+1]
            oft += 1
        oft += 2
        line = bytes((x ^ data[0]) for x in data[1:])
        lines = line.split(b'\r\n')
        for one in lines:
            if not one:
                yield b''
                continue
            if one[0] == 0xA1:
                yield bytes((x ^ one[0]) for x in one[1:])
            elif one[3:5] == b'\x00\xA1':
                yield from compat_read_lines(one, endline=None)
            else:
                yield one


def wxwork_logfile(filename):
    with open(filename, mode='rb') as f:
        content = f.read()
        yield from compat_read_lines(content)


def show(filename):
    (vp, vf) = os.path.split(filename)
    with open(vf, mode='w+b') as f:
        for line in wxwork_logfile(filename):
            f.write(line+b'\r\n')


if __name__ == '__main__':
    show(r'C:\Users\vip\AppData\Roaming\Tencent\WXWork\Log\2020-04-28_09-23-49_18(3.0.16.1614)_encrypt.log')


