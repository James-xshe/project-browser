# Project Browser

轻量项目浏览器 — 扫描 `~/projects/` 生成静态 dashboard，快速查看所有项目概览和文件结构。

## 功能

- 📂 项目卡片：名称、描述、技术栈、文件数、大小、最后修改时间
- 🔍 技术栈自动检测（package.json / requirements.txt / 文件扩展名）
- 🌳 文件树展开（递归 3 层，目录可折叠）
- 🔎 搜索过滤（名称 + 描述 + 技术栈，多关键词空格分隔）
- 📊 排序（名称 / 最近修改 / 大小）
- ⎇ Git / README 标识
- 📝 自定义描述（`.project.json` 的 description 字段）

## 快速开始

```bash
# 1. 扫描项目生成数据
python3 generate.py

# 2. 启动 HTTP 服务
python3 -m http.server 8765

# 3. 浏览器打开
open http://localhost:8765
```

## 自定义项目信息

在项目根目录创建 `.project.json`：

```json
{
  "name": "My Project",
  "description": "项目描述",
  "stack": ["python", "fastapi"],
  "created": "2026-05-01"
}
```

不填则自动从 README 和文件结构推断。

## 文件结构

```
project-browser/
├── .project.json    # 本项目元信息
├── generate.py      # 数据扫描脚本
├── data.json        # 生成的项目数据（gitignore）
├── index.html       # 单文件 dashboard
└── README.md
```

## 刷新数据

每次新增/删除项目后运行：

```bash
python3 generate.py
```

## 快捷键

| 键 | 功能 |
|----|------|
| `/` | 聚焦搜索框 |
| `Esc` | 关闭展开的卡片 / 失焦搜索 |

## 作为系统服务运行

```bash
# 已配置 systemd user service，开机自启
systemctl --user start project-browser
systemctl --user status project-browser
```

服务会在 `0.0.0.0:8765` 提供 dashboard，并在启动时自动刷新数据。

## 依赖

- Python 3.8+
- 无第三方依赖
