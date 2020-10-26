#!/usr/bin/env python3
# -*- coding:gbk -*-

import csv
import json
import logging
import re
from string import Template
from aliyunsdkcore import client
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.DescribeRegionsRequest import DescribeRegionsRequest

logging.basicConfig(filename='aliyun.log', level=logging.INFO, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s', datefmt='%a %d %b %Y %H:%M:%S')


class JsonWrapper:
    def __init__(self, json_value):
        self.array_index_pattern = re.compile('^\\$(?P<index>\\d+)(\\.(?P<subkey>.*))?')
        self.value = json_value

    def _subget(self, root: dict, key: str):
        key = key.lstrip('.')
        if not key:
            return None
        keys = key.split('.', maxsplit=1)
        parent = root.get(keys[0], None)
        if len(keys) == 1 or parent is None:
            return parent
        subkey = keys[1].lstrip('.')
        if not subkey:
            return parent
        if isinstance(parent, list):
            mr = self.array_index_pattern.match(subkey)
            if not mr:
                return None
            index = int(mr.group('index'))
            if index >= len(parent):
                return None
            array_item = parent[index]
            subkey = mr.group('subkey')
            if not subkey:
                return array_item
            if not isinstance(array_item, dict):
                return None
            return self._subget(array_item, subkey)
        elif isinstance(parent, dict):
            return self._subget(parent, subkey)
        else:
            return None

    def getex(self, key: str, default=None):
        return self._subget(self.value, key) or default

    def __getattr__(self, item):
        return getattr(self.value, item)

    def __str__(self):
        return str(self.value)


class ManagerClient:
    def __init__(self):
        self.alikeys = {}
        self.load_aliyun_keys(r'AliyunAccessKey.csv')

    def load_aliyun_keys(self, csv_filename):
        with open(csv_filename) as csvfile:
            reader = csv.reader(csvfile)
            keys = next(reader)
            values = next(reader)
            self.alikeys.update(dict(zip(keys, values)))

    def send_aliyun_request(self, request, region_id='cn-beijing'):
        aliyun = client.AcsClient(
            self.alikeys.get('AccessKey ID', None),
            self.alikeys.get('AccessKey Secret', None),
            region_id
        )
        request.set_accept_format('json')
        response_payload = aliyun.do_action_with_exception(request)
        with open(f'{region_id}.txt', 'w+') as f:
            f.write(response_payload.decode('utf-8'))
        # logging.info(response_payload)
        return JsonWrapper(json.loads(response_payload))

    def show_regions(self):
        request = DescribeRegionsRequest()
        result = self.send_aliyun_request(request)
        regions = result.getex('Regions.Region', [])
        print(regions)
        return regions

    def show_ecs_instances_in_region(self, region: dict):
        request = DescribeInstancesRequest()
        request.set_PageSize(100)
        detail = Template('ID: $instance_id, Name: $name, Status: $status, NetworkType: $network_type, IP: $ip($nip), OS: $os_name, CPU: $cpu($cpu_core_count x $threads_per_core), Memory: $memory')
        region_id = region.get('RegionId', '')
        has_more = True
        instances = []
        while has_more:
            result = self.send_aliyun_request(request, region_id)
            instances += result.getex('Instances.Instance', [])
            total_count = result.get('TotalCount', 0)
            page_size = result.get('PageSize', 10)
            page_number = result.get('PageNumber', 1)
            if page_number * page_size >= total_count:
                has_more = False
        print(f'{region_id}'.center(100, '-'))
        for instance in instances:
            item = JsonWrapper(instance)
            instance_network_type = item.get('InstanceNetworkType', 'classic')
            instance_ip = {
                'classic': '/'.join(item.getex('PublicIpAddress.IpAddress', [])),
                'vpc': item.getex('EipAddress.IpAddress', '')
            }
            instance_nip = {
                'classic': '/'.join(item.getex('InnerIpAddress.IpAddress', [])),
                'vpc': '/'.join(item.getex('VpcAttributes.PrivateIpAddress.IpAddress', []))
            }
            line = detail.substitute(
                instance_id=item.get('InstanceId', ''),
                name=item.get('InstanceName', ''),
                status=item.get('Status', ''),
                network_type=instance_network_type,
                ip=instance_ip.get(instance_network_type, ''),
                nip=instance_nip.get(instance_network_type, ''),
                os_name=item.get('OSName', ''),
                cpu=item.get('Cpu', 0),
                cpu_core_count=item.getex('CpuOptions.CoreCount', item.get('Cpu', 0)),
                threads_per_core=item.getex('CpuOptions.ThreadsPerCore', 1),
                memory='{}G'.format(int(item.get('Memory', 0)) / 1024)
            )
            print(line)

    def show_ecs_instances(self, regions: (list, tuple)):
        for region in regions:
            region_id = region.get('RegionId', '')
            #if not region_id.startswith('cn-'):
            #    continue
            self.show_ecs_instances_in_region(region)


manager = ManagerClient()
manager.show_ecs_instances(manager.show_regions())


