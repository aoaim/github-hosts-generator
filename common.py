#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author      :   aoaim
#   Orig Author :   XueWeiHan
#   Date        :   2025-03-18
#   Desc        :   公共文件写入函数
import os
import json
from datetime import datetime, timezone, timedelta

HOSTS_TEMPLATE = """# GitHub Hosts Generator Start
{content}# Update time: {update_time}
# GitHub Hosts Generator End
"""


def write_host_file(hosts_content: str) -> None:
    """写入 hosts 文件"""
    output_file_path = os.path.join(os.path.dirname(__file__), 'hosts')
    with open(output_file_path, "w") as output_fb:
        output_fb.write(hosts_content)


def write_json_file(hosts_list: list) -> None:
    """写入 JSON 文件"""
    output_file_path = os.path.join(os.path.dirname(__file__), 'hosts.json')
    with open(output_file_path, "w") as output_fb:
        json.dump(hosts_list, output_fb)


def write_hosts_content(content: str, content_list: list) -> str:
    """
    写入 hosts 内容
    
    Args:
        content: hosts 内容
        content_list: hosts 列表（用于生成 JSON）
    """
    if not content:
        return ""
    
    update_time = datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=8))).replace(microsecond=0).isoformat()
    
    hosts_content = HOSTS_TEMPLATE.format(
        content=content,
        update_time=update_time
    )
    
    write_host_file(hosts_content)
    write_json_file(content_list)
    
    return hosts_content
