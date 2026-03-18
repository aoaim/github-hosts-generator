#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author      :   aoaim
#   Date        :   2025-03-18
#   Desc        :   自动应用 hosts 到系统
import os
import platform
import subprocess
import shutil
from datetime import datetime


def get_system_hosts_path():
    """获取系统 hosts 文件路径"""
    system = platform.system()
    if system == 'Windows':
        return r'C:\Windows\System32\drivers\etc\hosts'
    elif system == 'Darwin':  # macOS
        return '/etc/hosts'
    else:  # Linux
        return '/etc/hosts'


def backup_hosts(system_hosts_path):
    """备份系统 hosts"""
    backup_path = f"{system_hosts_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(system_hosts_path, backup_path)
        print(f"✓ 已备份原 hosts: {backup_path}")
        return backup_path
    except PermissionError:
        # 权限不足，使用 sudo cp
        try:
            subprocess.run(['sudo', 'cp', system_hosts_path, backup_path], check=True)
            print(f"✓ 已使用 sudo 备份原 hosts: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"✗ 备份失败: {e}")
            return None
    except Exception as e:
        print(f"✗ 备份失败: {e}")
        return None


def merge_hosts(system_hosts_path, new_hosts_path):
    """合并 hosts，保留用户自定义内容，替换 GitHub520 部分"""
    
    # 读取新生成的 hosts
    with open(new_hosts_path, 'r', encoding='utf-8') as f:
        new_hosts = f.read()
    
    # 如果系统 hosts 不存在，直接写入
    if not os.path.exists(system_hosts_path):
        return new_hosts
    
    # 读取系统 hosts
    with open(system_hosts_path, 'r', encoding='utf-8') as f:
        system_hosts = f.read()
    
    # 查找并删除旧的 GitHub520 配置
    start_marker = '# GitHub520 Host Start'
    end_marker = '# GitHub520 Host End'
    
    if start_marker in system_hosts and end_marker in system_hosts:
        # 找到 GitHub520 部分并删除
        before = system_hosts.split(start_marker)[0]
        after = system_hosts.split(end_marker)[1]
        # 清理多余的空行
        before = before.rstrip() + '\n\n' if before.strip() else ''
        after = after.lstrip()
        system_hosts = before + after
    
    # 在文件末尾添加新的 hosts（如果文件不为空，先加换行）
    if system_hosts.strip():
        if not system_hosts.endswith('\n'):
            system_hosts += '\n'
        system_hosts += '\n'
    
    return system_hosts + new_hosts


def apply_hosts():
    """应用 hosts 到系统"""
    
    # 获取路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    new_hosts_path = os.path.join(script_dir, 'hosts')
    system_hosts_path = get_system_hosts_path()
    
    # 检查生成的 hosts 是否存在
    if not os.path.exists(new_hosts_path):
        print("✗ 未找到生成的 hosts 文件，请先运行 fetch_ips.py")
        return False
    
    print(f"系统 hosts 路径: {system_hosts_path}")
    print(f"新生成 hosts: {new_hosts_path}")
    
    # 备份原 hosts
    backup_path = backup_hosts(system_hosts_path)
    if not backup_path:
        response = input("备份失败，是否继续? (y/N): ")
        if response.lower() != 'y':
            return False
    
    # 合并 hosts
    merged_content = merge_hosts(system_hosts_path, new_hosts_path)
    
    # 写入系统 hosts（需要管理员权限）
    try:
        # 先尝试直接写入
        with open(system_hosts_path, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        print(f"✓ 成功写入系统 hosts")
    except PermissionError:
        # 权限不足，使用 sudo
        print("需要管理员权限，尝试使用 sudo...")
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.hosts', delete=False) as tmp:
            tmp.write(merged_content)
            tmp_path = tmp.name
        
        try:
            subprocess.run(['sudo', 'cp', tmp_path, system_hosts_path], check=True)
            os.unlink(tmp_path)
            print(f"✓ 成功使用 sudo 写入系统 hosts")
        except subprocess.CalledProcessError as e:
            print(f"✗ 写入失败: {e}")
            return False
        except FileNotFoundError:
            print("✗ 未找到 sudo 命令，请手动运行: sudo cp hosts /etc/hosts")
            return False
    except Exception as e:
        print(f"✗ 写入失败: {e}")
        return False
    
    # 刷新 DNS 缓存
    flush_dns()
    
    return True


def flush_dns():
    """刷新 DNS 缓存"""
    system = platform.system()
    
    commands = {
        'Windows': ['ipconfig', '/flushdns'],
        'Darwin': ['sudo', 'killall', '-HUP', 'mDNSResponder'],
        'Linux': None  # Linux 有多种方式，单独处理
    }
    
    if system == 'Linux':
        # 尝试多种 Linux DNS 刷新方式
        linux_commands = [
            ['sudo', 'systemd-resolve', '--flush-caches'],
            ['sudo', 'nscd', '-i', 'hosts'],
            ['sudo', '/etc/init.d/nscd', 'restart'],
        ]
        for cmd in linux_commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"✓ DNS 缓存已刷新")
                return
            except:
                continue
        print("⚠ 请手动刷新 DNS: sudo systemd-resolve --flush-caches 或重启网络服务")
    else:
        cmd = commands.get(system)
        if cmd:
            try:
                subprocess.run(cmd, check=True)
                print(f"✓ DNS 缓存已刷新")
            except Exception as e:
                print(f"⚠ DNS 刷新失败: {e}")


if __name__ == '__main__':
    print("=" * 50)
    print("GitHub520 Hosts 自动应用工具")
    print("=" * 50)
    print()
    
    if apply_hosts():
        print()
        print("✓ 完成！hosts 已应用到系统")
    else:
        print()
        print("✗ 应用失败")
        exit(1)
