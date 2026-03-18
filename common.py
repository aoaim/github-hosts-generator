#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author      :   aoaim
#   Orig Author :   XueWeiHan
#   Date        :   2025-03-18
#   Desc        :   公共函数和域名列表
import os
import json
from typing import Any, Optional
from datetime import datetime, timezone, timedelta

GITHUB_URLS = [
    'alive.github.com', 'api.github.com', 'api.individual.githubcopilot.com',
    'avatars.githubusercontent.com', 'avatars0.githubusercontent.com',
    'avatars1.githubusercontent.com', 'avatars2.githubusercontent.com',
    'avatars3.githubusercontent.com', 'avatars4.githubusercontent.com',
    'avatars5.githubusercontent.com', 'camo.githubusercontent.com',
    'central.github.com', 'cloud.githubusercontent.com', 'codeload.github.com',
    'collector.github.com', 'desktop.githubusercontent.com',
    'favicons.githubusercontent.com', 'gist.github.com',
    'github-cloud.s3.amazonaws.com', 'github-com.s3.amazonaws.com',
    'github-production-release-asset-2e65be.s3.amazonaws.com',
    'github-production-repository-file-5c1aeb.s3.amazonaws.com',
    'github-production-user-asset-6210df.s3.amazonaws.com', 'github.blog',
    'github.com', 'github.community', 'github.githubassets.com',
    'github.global.ssl.fastly.net', 'github.io', 'github.map.fastly.net',
    'githubstatus.com', 'live.github.com', 'media.githubusercontent.com',
    'objects.githubusercontent.com', 'pipelines.actions.githubusercontent.com',
    'raw.githubusercontent.com', 'user-images.githubusercontent.com',
    'vscode.dev', 'education.github.com', 'private-user-images.githubusercontent.com'
]

HOSTS_TEMPLATE = """# GitHub520 Host Start
# Network: {network_info}
{content}# Update time: {update_time}
# GitHub520 Host End
"""


def get_network_str() -> str:
    """获取网络环境字符串"""
    try:
        from network_detector import get_network_info, format_network_info
        info = get_network_info()
        return format_network_info(info)
    except Exception:
        return "Unknown"


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


def update_readme(hosts_content: str, update_time: str) -> None:
    """更新 README.md，将最新的 hosts 写入"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    
    if not os.path.exists(readme_path):
        return
    
    # 读取现有 README
    with open(readme_path, 'r') as f:
        readme_content = f.read()
    
    # 查找 hosts 代码块并替换
    start_marker = '## 最新 Hosts'
    end_marker = '## 使用方法'
    
    new_section = f"""## 最新 Hosts

> 生成时间: {update_time}

```bash
{hosts_content}```

## 使用方法"""
    
    if start_marker in readme_content and end_marker in readme_content:
        # 替换现有部分
        before = readme_content.split(start_marker)[0]
        after = readme_content.split(end_marker)[1]
        readme_content = before + new_section + after
    else:
        # 在文件开头添加
        readme_content = new_section + '\n\n' + readme_content
    
    with open(readme_path, 'w') as f:
        f.write(readme_content)


def write_hosts_content(content: str, content_list: list, network_info: str = "") -> str:
    """
    写入 hosts 内容
    
    Args:
        content: hosts 内容
        content_list: hosts 列表（用于生成 JSON）
        network_info: 网络环境信息
    """
    if not content:
        return ""
    
    update_time = datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=8))).replace(microsecond=0).isoformat()
    
    if not network_info:
        network_info = get_network_str()
    
    hosts_content = HOSTS_TEMPLATE.format(
        network_info=network_info,
        content=content,
        update_time=update_time
    )
    
    write_host_file(hosts_content)
    write_json_file(content_list)
    update_readme(hosts_content, update_time)
    
    return hosts_content
