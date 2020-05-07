#!/usr/bin/env python

import os
import sys
import shutil
import fnmatch
import xml.dom.minidom as xmldom
from xml.dom import Node


def find_packages(path, arch=None):
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        for dirname in dirnames:
            if os.path.exists(os.path.join(dirpath, dirname, 'include')):
                if not arch or dirname.endswith(arch):
                    yield dirname


def find_vcxproj_files(path):
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, '*.vcxproj'):
            yield os.path.join(dirpath, filename)


def add_keys_to_node(node, data):
    new = [] + data
    for child in node.childNodes:
        if child.nodeType == node.TEXT_NODE:
            new += child.nodeValue.split(';')
            new = list(set(new))
            new.sort(key=lambda x: ('~'+x) if x[0] in ['$', '%'] else x)
            child.nodeValue = ';'.join(new)


def add_to_all_files(element, include_dirs, library_dirs):
    name = element.nodeName
    if name.endswith('AdditionalIncludeDirectories'):
        add_keys_to_node(element, include_dirs)
    elif name.endswith('AdditionalLibraryDirectories'):
        add_keys_to_node(element, library_dirs)
    # elif name.endswith('AdditionalDependencies'):
    #     add_keys_to_node(element, LIBRARIES)
    for child in element.childNodes:
        add_to_all_files(child, include_dirs, library_dirs)


def add_vcpkg_dirs(filename, include_dirs, library_dirs):
    dom = xmldom.parse(filename)
    root = dom.documentElement
    add_to_all_files(root, include_dirs, library_dirs)
    os.rename(filename, filename+'.bak')
    with open(filename, 'wt') as f:
        dom.writexml(f, encoding='UTF-8')


def make_vcxproj_patch(filename):
    vcpkg = os.environ.get('vcpkg', None)
    if not vcpkg:
        return 0
    packages = [package for package in find_packages(vcpkg)]
    include_dirs = [os.path.join(vcpkg, package, 'include') for package in packages]
    library_dirs = [os.path.join(vcpkg, package, 'lib') for package in packages]
    add_vcpkg_dirs(filename, include_dirs, library_dirs)


def pretty(node):
    if node.hasChildNodes():
        for child in node.childNodes:
            pretty(child)
    else:
        if node.nodeType == Node.TEXT_NODE:
            node.nodeValue = node.nodeValue.strip(' \t\r\n')


def make_vcxproj_template():
    vcpkg = os.environ.get('vcpkg', None)
    if not vcpkg:
        return None
    packages = [package for package in find_packages(vcpkg)]
    include_dirs = [os.path.join(vcpkg, package, 'include') for package in packages]
    library_dirs = [os.path.join(vcpkg, package, 'lib') for package in packages]
    execute_dirs = [os.path.join(vcpkg, package, 'bin') for package in packages]

    include_dirs.append('$(IncludePath)')
    library_dirs.append('$(LibraryPath)')
    #execute_dirs.append('$(ExecutablePath)')

    local_app_data = os.environ.get('LOCALAPPDATA', '')
    user_root_dir = os.path.join(local_app_data, 'Microsoft\\MSBuild\\v4.0')
    print(user_root_dir)
    user_props_file = os.path.join(user_root_dir, "Microsoft.Cpp.Win32.user.props")
    backup_file = user_props_file + '.bak'
    shutil.copy(backup_file, user_props_file)
    dom = xmldom.parse(user_props_file)
    doc = dom.childNodes[0]
    property_group = dom.createElement('PropertyGroup')
    include_path = dom.createElement('IncludePath')
    library_path = dom.createElement('LibraryPath')
    execute_path = dom.createElement('ExecutablePath')
    local_environment = dom.createElement('LocalDebuggerEnvironment')
    item_definition_group = dom.createElement('ItemDefinitionGroup')
    cl_compile = dom.createElement('ClCompile')
    additional_inc_dirs = dom.createElement('AdditionalIncludeDirectories')
    vcpkg_include_dirs = dom.createTextNode(';'.join(include_dirs))
    vcpkg_library_dirs = dom.createTextNode(';'.join(library_dirs))
    vcpkg_execute_dirs = dom.createTextNode(';'.join(execute_dirs))
    vcpkg_execute_path = dom.createTextNode('PATH='+';'.join(execute_dirs)+';\n$(LocalDebuggerEnvironment)')
    solution_dir = dom.createTextNode('$(SolutionDir)')
    include_path.appendChild(vcpkg_include_dirs)
    library_path.appendChild(vcpkg_library_dirs)
    execute_path.appendChild(vcpkg_execute_dirs)
    local_environment.appendChild(vcpkg_execute_path)
    additional_inc_dirs.appendChild(solution_dir)
    property_group.childNodes.append(include_path)
    property_group.childNodes.append(library_path)
    #property_group.childNodes.append(execute_path)
    property_group.childNodes.append(local_environment)
    cl_compile.appendChild(additional_inc_dirs)
    item_definition_group.childNodes.append(cl_compile)
    doc.childNodes.append(property_group)
    doc.childNodes.append(item_definition_group)
    if not os.path.exists(backup_file):
        os.rename(user_props_file, backup_file)
    pretty(doc)
    dom.normalize()
    with open(user_props_file, 'w', encoding='UTF-8') as f:
        dom.writexml(f, indent='\n', addindent='  ', encoding='UTF-8')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        make_vcxproj_template()
    else:
        make_vcxproj_patch(args)
    sys.exit(0)

