#!/usr/bin/env python

import sys
import re

vers = [
    'FILEVERSION',
    'PRODUCTVERSION',
    'FileVersion',
    'ProductVersion'
]

new_version = lambda m: m.group('major') + ',' + m.group('minor') + ',' + m.group('revision') + ',' + str(int(m.group('build'))+1)
#def new_version(m):
#    return m.group('major') + ',' + m.group('minor') + ',' + m.group('revision') + ',' + str(int(m.group('build'))+1)

def make_new_version(filename):
    all = ''
    with open(filename, 'r+') as file:
        for line in file:
            for vstr in vers:
                if vstr in line:
                    line = re.sub(r'(?P<major>\d+),([ ]+)?(?P<minor>\d+),([ ]+)?(?P<revision>\d+),([ ]+)?(?P<build>\d+)', new_version, line, flags=re.IGNORECASE)
            all = all + line
        file.seek(0)
        file.write(all)

def main(argv):
    if len(argv) < 2:
        return
    make_new_version(argv[1])


if __name__ == '__main__':
    main(sys.argv)
