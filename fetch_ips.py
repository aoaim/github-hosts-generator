#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author      :   aoaim
#   Orig Author :   XueWeiHan
#   Date        :   2025-03-18
#   Desc        :   获取 GitHub 域名的最优 IP 地址，使用 TCP 连接测试无需 root 权限
import re
import socket
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
import sys
import asyncio
import aiodns

from requests_html import HTMLSession
from retry import retry

from common import GITHUB_URLS, write_hosts_content


TCP_TIMEOUT_SEC: float = 2.0
DISCARD_LIST: List[str] = ["1.0.1.1", "1.2.1.1", "127.0.0.1"]


TCP_LIST: Dict[str, float] = dict()


def tcp_connect_time(ip: str, port: int = 80) -> float:
    """使用 TCP 连接测试延迟，不需要 root 权限"""
    global TCP_LIST
    if ip in TCP_LIST:
        return TCP_LIST[ip]
    
    times = []
    for _ in range(3):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TCP_TIMEOUT_SEC)
            sock.connect((ip, port))
            sock.close()
            elapsed = (time.time() - start) * 1000  # 转换为毫秒
            times.append(elapsed)
        except (socket.timeout, socket.error, OSError):
            times.append(TCP_TIMEOUT_SEC * 1000)
    
    times.sort()
    result = times[1]  # 取中位数
    print(f'TCP connect {ip}:{port}: {result:.1f} ms')
    TCP_LIST[ip] = result
    return result


def select_ip_from_list(ip_list: List[str]) -> Optional[str]:
    if len(ip_list) == 0:
        return None
    
    # 测试每个 IP 的 TCP 连接延迟
    tcp_results = []
    for ip in ip_list:
        try:
            delay = tcp_connect_time(ip, 443)  # 测试 HTTPS 端口
            tcp_results.append((ip, delay))
        except Exception as e:
            print(f"  Error testing {ip}: {e}")
            tcp_results.append((ip, TCP_TIMEOUT_SEC * 1000))
    
    # 按延迟排序
    tcp_results.sort(key=lambda x: x[1])
    
    # 优先选择能正常连接（未超时）的 IP
    timeout_threshold = TCP_TIMEOUT_SEC * 1000
    working_ips = [(ip, delay) for ip, delay in tcp_results if delay < timeout_threshold]
    
    if working_ips:
        # 有能连接的 IP，选择延迟最低的
        best_ip = working_ips[0][0]
        best_delay = working_ips[0][1]
        print(f"Results: {[(ip, f'{delay:.1f}ms') for ip, delay in tcp_results[:5]]}")
        print(f"Selected working IP: {best_ip} ({best_delay:.1f}ms)")
    else:
        # 全都超时，选择延迟最低的那个（会标记为 Timeout）
        best_ip = tcp_results[0][0]
        print(f"Results: {[(ip, f'{delay:.1f}ms') for ip, delay in tcp_results[:5]]}")
        print(f"All IPs timeout, selected best: {best_ip}")
    
    return best_ip


@retry(tries=3)
def get_ip_list_from_ipaddress_com(session: Any, github_url: str) -> Optional[List[str]]:
    url = f'https://sites.ipaddress.com/{github_url}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                      ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1'
                      '06.0.0.0 Safari/537.36'}
    try:
        rs = session.get(url, headers=headers, timeout=5)
        pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ip_list = re.findall(pattern, rs.html.text)
        return ip_list
    except Exception as ex:
        print(f"get: {url}, error: {ex}")
        raise Exception


DNS_SERVER_LIST = [
    "1.1.1.1",      # Cloudflare
    "8.8.8.8",      # Google
    "9.9.9.9",      # Quad9
    "119.29.29.29", # DNSPod (腾讯)
    "223.5.5.5",    # AliDNS (阿里)
    "180.184.1.1",  # ByteDNS (字节跳动)
    "101.101.101.101",  # Quad101
    "101.102.103.104",  # Quad101
    "114.114.114.114",  # 114DNS
    "182.254.116.116",  # DNSPod 备用
    "1.2.4.8",          # CNNIC
    "208.67.222.222",   # OpenDNS
]


def windows_compatibility_check():
    if sys.platform == "win32":
        try:
            import pycares
        except ImportError:
            raise RuntimeError("请先执行 'pip install pycares'")


async def get_ip_list_from_dns(
    domain,
    record_type="A",
    dns_server_list=None,
):
    if dns_server_list is None:
        dns_server_list = DNS_SERVER_LIST
    windows_compatibility_check()
    resolver = aiodns.DNSResolver()
    resolver.nameservers = dns_server_list

    try:
        result = await resolver.query_dns(domain, record_type)
        # query_dns returns DNSResult with answer list
        ip_list = []
        for record in result.answer:
            # Get IP address from A record
            addr = getattr(record.data, 'addr', None)
            if addr:
                ip_list.append(addr)
        return ip_list
    except aiodns.error.DNSError as e:
        print(f"{domain}: DNS 查询失败: {e}")
        return []


async def get_ip(session: Any, github_url: str) -> Optional[str]:
    ip_list_web = []
    try:
        ip_list_web = get_ip_list_from_ipaddress_com(session, github_url)
    except Exception as ex:
        pass
    ip_list_dns = []
    try:
        ip_list_dns = await get_ip_list_from_dns(github_url, dns_server_list=DNS_SERVER_LIST)
    except Exception as ex:
        pass
    ip_list_set = set(ip_list_web + ip_list_dns)
    for discard_ip in DISCARD_LIST:
        ip_list_set.discard(discard_ip)
    ip_list = list(ip_list_set)
    ip_list.sort()
    if len(ip_list) == 0:
        return None
    print(f"{github_url}: {ip_list}")
    best_ip = select_ip_from_list(ip_list)
    return best_ip


async def main() -> None:
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'{current_time} - Start script.')

    session = HTMLSession()
    content = ""
    content_list = []
    success_count = 0

    for index, github_url in enumerate(GITHUB_URLS):
        print(f'Start Processing url: {index + 1}/{len(GITHUB_URLS)}, {github_url}')
        try:
            ip = await get_ip(session, github_url)
            if ip is None:
                print(f"{github_url}: IP Not Found")
                ip = "# IP Address Not Found"
            content += ip.ljust(30) + github_url
            global TCP_LIST
            if TCP_LIST.get(ip) is not None and TCP_LIST.get(ip) >= TCP_TIMEOUT_SEC * 1000:
                content += "  # Timeout"
            content += "\n"
            content_list.append((ip, github_url,))
            success_count += 1
        except Exception:
            continue

    # 检查是否成功获取了数据
    if success_count == 0:
        print("✗ 未能获取任何 IP，保留旧 hosts 文件")
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'{current_time} - End script.')
        return

    # 成功获取数据后，删除旧文件
    import os
    for f in ['hosts', 'hosts.json']:
        if os.path.exists(f):
            os.remove(f)
            print(f'已删除旧文件: {f}')

    write_hosts_content(content, content_list)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'{current_time} - End script.')


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
