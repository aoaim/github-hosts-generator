#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author      :   aoaim
#   Date        :   2025-03-18
#   Desc        :   网络环境探测工具（多源）
import requests
import json


def get_network_info_pconline() -> dict:
    """使用 pconline 获取网络信息"""
    try:
        url = 'https://whois.pconline.com.cn/ipJson.jsp?json=true'
        response = requests.get(url, timeout=5)
        response.encoding = 'gbk'
        data = response.json()
        
        if 'ip' in data:
            addr = data.get('addr', '')
            isp = extract_isp(addr)
            
            return {
                'ip': data.get('ip', 'Unknown'),
                'location': f"{data.get('pro', '')} {data.get('city', '')}".strip(),
                'isp': isp,
                'org': addr,
                'source': 'pconline'
            }
    except Exception as e:
        print(f"pconline 查询失败: {e}")
    
    return None


def get_network_info_ipip() -> dict:
    """使用 ipip.net 获取网络信息（非常稳定）"""
    try:
        url = 'https://myip.ipip.net/json'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if data.get('data'):
            location_data = data['data']
            country = location_data.get('location', [''])[0] if location_data.get('location') else ''
            province = location_data.get('location', ['', ''])[1] if len(location_data.get('location', [])) > 1 else ''
            city = location_data.get('location', ['', '', ''])[2] if len(location_data.get('location', [])) > 2 else ''
            isp = location_data.get('location', ['', '', '', '', ''])[4] if len(location_data.get('location', [])) > 4 else ''
            
            return {
                'ip': location_data.get('ip', 'Unknown'),
                'location': f"{province} {city}".strip(),
                'isp': extract_isp(isp) if isp else 'Unknown',
                'org': isp,
                'source': 'ipip.net'
            }
    except Exception as e:
        print(f"ipip.net 查询失败: {e}")
    
    return None


def get_network_info_bilibili() -> dict:
    """使用 B站 API 获取网络信息（大厂稳定）"""
    try:
        url = 'https://api.bilibili.com/x/web-interface/zone'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if data.get('data'):
            d = data['data']
            return {
                'ip': d.get('addr', 'Unknown'),
                'location': f"{d.get('province', '')} {d.get('city', '')}".strip(),
                'isp': extract_isp(d.get('isp', '')),
                'org': d.get('isp', ''),
                'source': 'bilibili'
            }
    except Exception as e:
        print(f"bilibili 查询失败: {e}")
    
    return None


def get_network_info_163() -> dict:
    """使用网易 163 获取网络信息"""
    try:
        url = 'https://dashi.163.com/fgw/mailsrv-ipdetail/detail'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if data.get('result'):
            result = data['result']
            return {
                'ip': result.get('ip', 'Unknown'),
                'location': f"{result.get('province', '')} {result.get('city', '')}".strip(),
                'isp': extract_isp(result.get('operator', '') or result.get('org', '')),
                'org': result.get('operator', '') or result.get('org', ''),
                'source': '163'
            }
    except Exception as e:
        print(f"163 查询失败: {e}")
    
    return None


def extract_isp(text: str) -> str:
    """从文本中提取运营商信息"""
    if not text:
        return 'Unknown'
    
    text = str(text)
    if '电信' in text:
        return '电信'
    elif '联通' in text:
        return '联通'
    elif '移动' in text:
        return '移动'
    elif '铁通' in text:
        return '铁通'
    elif '长城' in text:
        return '长城宽带'
    elif '教育网' in text or '校园网' in text:
        return '教育网'
    elif '广电' in text:
        return '广电'
    elif '鹏博士' in text:
        return '鹏博士'
    
    return text.strip() if text else 'Unknown'


def get_network_info() -> dict:
    """
    获取当前网络环境信息（多源fallback）
    按优先级尝试多个接口
    """
    # 定义查询函数列表（按优先级排序）
    providers = [
        get_network_info_ipip,      # ipip.net 最稳定
        get_network_info_pconline,  # pconline
        get_network_info_bilibili,  # B站
        get_network_info_163,       # 网易
    ]
    
    for provider in providers:
        try:
            result = provider()
            if result:
                print(f"使用 {result['source']} 获取网络信息: {result['location']} {result['isp']}")
                return result
        except Exception as e:
            print(f"{provider.__name__} 失败: {e}")
            continue
    
    return {
        'ip': 'Unknown',
        'location': 'Unknown',
        'isp': 'Unknown',
        'org': '',
        'source': 'failed'
    }


def format_network_info(info: dict) -> str:
    """格式化网络信息为字符串"""
    if info['isp'] == 'Unknown':
        return "未知网络"
    
    location = info['location'].replace('China ', '').replace('中国 ', '').strip()
    return f"{location} {info['isp']}"


if __name__ == '__main__':
    info = get_network_info()
    print(f"\n最终信息:")
    print(f"IP: {info['ip']}")
    print(f"位置: {info['location']}")
    print(f"ISP: {info['isp']}")
    print(f"详细信息: {info['org']}")
    print(f"来源: {info['source']}")
    print(f"格式化: {format_network_info(info)}")
