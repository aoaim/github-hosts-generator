# GitHub520

在本地根据云端收集的候选 IP 自动测试连通性，生成可用的 GitHub hosts 映射，改善中国大陆网络环境下的访问稳定性。

## 项目做什么

1. GitHub Action（境外运行）定期生成 `raw_ips.json`。
2. 本地脚本 `select_ips.py` 读取 `raw_ips.json`，对每个域名候选 IP 做 TCP 443 测试。
3. 为每个域名选择本地可用且延迟最低的 IP，输出 `hosts`、`hosts.json` 和 `connectivity_report.json`。

## 使用方法

1. 拉取仓库最新内容（确保包含最新 `raw_ips.json`）。
2. 在项目根目录运行：

```bash
python select_ips.py
```

3. 生成文件：
   - `hosts`: 可直接使用的 hosts 内容
   - `hosts.json`: 域名与选中 IP 列表
   - `connectivity_report.json`: 本地连通性测试明细（含候选 IP 与延迟）

## 说明

- 域名列表维护在 `domains.py`。
- GitHub Action 工作流在 `.github/workflows/fetch-ips.yml`。
