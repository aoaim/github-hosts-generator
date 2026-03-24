# Hosts Generator

在本地根据云端收集的候选 IP 自动测试连通性，生成可用的 hosts 映射。当前默认目标是 GitHub 相关域名，但后续可以通过扩充目标域名列表继续扩展。

## 项目做什么

1. GitHub Action（境外运行）定期生成 `output/raw_ips.json`。
2. 根目录入口脚本 `generate_hosts.py` 读取 `output/raw_ips.json`，对每个目标域名候选 IP 做 TCP 443 测试。
3. 为每个域名选择本地可用且延迟最低的 IP，输出到 `output/` 目录。

## 使用方法

1. 拉取仓库最新内容（确保包含最新 `output/raw_ips.json`）。
2. 在项目根目录运行：

```bash
python generate_hosts.py
```

如果你的终端里 `python` 不是当前环境解释器，也可以显式使用你自己的环境命令执行。

3. 生成文件：
   - `output/hosts`: 可直接使用的 hosts 内容
   - `output/hosts.json`: 域名与选中 IP 列表
   - `output/connectivity_report.json`: 本地连通性测试明细（含候选 IP 与延迟）
   - `output/raw_ips.json`: GitHub Action 收集的候选 IP 数据

## 说明

- 业务代码集中放在 `hostsgen/`，根目录只保留直接执行的 `generate_hosts.py`。
- 目标域名列表维护在 `hostsgen/config.py` 的 `TARGET_DOMAINS`。
- `.github/scripts/fetch_ips_action.py` 仅保留为 GitHub Action 入口包装器。
- 所有生成产物统一放在 `output/` 目录，便于提交和清理。
- GitHub Action 工作流在 `.github/workflows/fetch-ips.yml`。
