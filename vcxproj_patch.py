#!/usr/bin/env python

import os
import fnmatch
import xml.dom.minidom as xmldom

INCLUDES = [
    '$(openssl)\\include',
    '$(pthread)\\include',
    '$(c_ares)\\include',
    '$(libwebsockets)\\include'
]


LIBPATH = [
    '$(openssl)\\lib',
    '$(pthread)\\lib\\x86',
    '$(c_ares)\\lib',
    '$(libwebsockets)\\lib',
    '$(OutDir)'
]


LIBRARIES = [
    'ssleay32.lib',
    'libeay32.lib',
    'pthreadVCE2.lib',
    'cares.lib',
    'libcares.lib',
    'websockets.lib'
]


def find_files(path, filters):
    for root, dirs, files in os.walk(path):
        for file in fnmatch.filter(files, filters):
            yield os.path.join(root, file), file


def patch_node(node, data):
    new = [] + data
    for child in node.childNodes:
        if child.nodeType == node.TEXT_NODE:
            new += child.nodeValue.split(';')
            new = list(set(new))
            new.sort(key=lambda x: ('~'+x) if x[0] in ['$', '%'] else x)
            child.nodeValue = ';'.join(new)


def patch_all_files(element):
    name = element.nodeName
    if name.endswith('AdditionalIncludeDirectories'):
        patch_node(element, INCLUDES)
    elif name.endswith('AdditionalLibraryDirectories'):
        patch_node(element, LIBPATH)
    elif name.endswith('AdditionalDependencies'):
        patch_node(element, LIBRARIES)

    for child in element.childNodes:
        patch_all_files(child)


def start_patch(path):
    for file, short_name in find_files(path, '*.vcxproj'):
        dom = xmldom.parse(file)
        root = dom.documentElement
        patch_all_files(root)
        # os.rename(file, file+'.bak')
        with open(file, 'wt') as f:
            dom.writexml(f, encoding='UTF-8')


if __name__ == '__main__':
    start_patch(r'F:\develop\mosquitto\build')

