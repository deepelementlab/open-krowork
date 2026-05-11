<p align="center">
  <img width="200" height="200" alt="workFlow" src="https://github.com/user-attachments/assets/41cebbbc-f2f4-464e-baa1-d83ecc290998" />
</p>


<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-MCP_服务器-blue?style=for-the-badge&labelColor=1a1a2e" alt="Claude Code MCP">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/平台-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge" alt="Platform">
</p>

<h1 align="center">Open-KroWork</h1>

<p align="center"><strong>一句话，变成桌面应用。零代码，零 Token。</strong></p>

<p align="center">
  Open-KroWork 是一个 <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> 插件，把自然语言描述的工作流<br>
  自动转换为可独立运行的本地桌面应用。说一句话，得一个带桌面图标的完整应用。
</p>

<p align="center">
  <a href="./README.md">English</a> | <a href="./README_CN.md">中文</a>
</p>

---

> **关于本项目：** Open-KroWork 是 [KroWork](https://krowork.com/) 核心理念的开源实现 — 将自然语言工作流转化为本地桌面应用。本项目由社区驱动，**非**快手官方产品，也非 KroWork 团队开发。基于 [MCP 协议](https://modelcontextprotocol.io/)构建，作为 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 的 MCP 服务器运行。

---

<img width="1990" height="720" alt="Screenshot - 2026-05-11 10 44 35" src="https://github.com/user-attachments/assets/5122b44e-4691-4fdd-8566-4871c7f90446" />

## 它能做什么

```
你:  "帮我做一个股票智能分析台，输入股票代码，自动展示价格趋势并生成分析报告"
KroWork: 自动生成完整应用 → 安装依赖 → 创建桌面快捷方式
你:  双击桌面图标，应用直接运行。不再需要 Claude。
```
<img width="2574" height="1070" alt="Screenshot - 2026-05-11 10 53 04" src="https://github.com/user-attachments/assets/e4bbbbf6-2e0a-4657-95fd-a9b8c529c47a" />


**核心理念：「跑通一次，变成应用」**

| 用 KroWork 之前 | 用 KroWork 之后 |
|---|---|
| 每天重复输入相同的 Prompt | 双击桌面图标，一秒启动 |
| 每次消耗 Token，成本线性增长 | 应用本地运行，零 Token 消耗 |
| 同一 Prompt 结果不稳定 | 确定性执行，100% 稳定 |
| 数据上传到云端 | 全部数据留在本地 |

---

## 效果演示

### 一句话创建应用

```
> /krowork:create "Todo管理器 - 管理任务和待办事项，支持优先级和状态"

✓ 应用 "todo-manager" 创建成功
✓ 依赖已安装 (flask)
✓ 桌面快捷方式已创建: ~/Desktop/KroWork - Todo管理器.lnk
✓ 运行在 http://127.0.0.1:5000
```

### 你会得到什么

一个完整的 Flask Web 应用，包括：
- 暗色主题响应式界面
- 完整的 CRUD API（增删改查）
- 实时更新的交互前端
- 桌面快捷方式 — 双击启动，告别命令行

### 一键迭代改进

```
> /krowork:improve todo-manager "添加CSV导出和搜索功能"

✓ 已添加 CSV 导出（下载按钮）
✓ 已添加搜索功能（关键词过滤）
✓ 版本更新至 v1.0.2
```

---

## 功能全景

### 应用生命周期

| 功能 | 命令 | 说明 |
|---|---|---|
| 创建 | `/krowork:create` | 从自然语言自动生成完整应用 |
| 运行 | `/krowork:run` | 沙箱隔离启动，自动打开浏览器 |
| 改进 | `/krowork:improve` | 一键改进：加字段、加导出、换主题、设定时 |
| 删除 | `/krowork:delete` | 彻底删除应用及所有文件 |

### 33 个 MCP 工具

<details>
<summary><strong>应用管理 (10)</strong></summary>

- `krowork_create_app` — 从描述自动生成应用（含代码、模板、依赖）
- `krowork_list_apps` — 列出所有应用
- `krowork_get_app` — 获取应用详情和源码
- `krowork_run_app` — 启动应用，返回访问地址
- `krowork_stop_app` — 停止运行中的应用
- `krowork_update_app` — 更新代码/模板/依赖
- `krowork_delete_app` — 永久删除应用
- `krowork_app_status` — 检查应用运行状态
- `krowork_get_app_log` — 获取应用日志
- `krowork_create_shortcut` — 创建桌面快捷方式
</details>

<details>
<summary><strong>网页抓取 (7)</strong></summary>

- `krowork_scrape_page` — 抓取网页：标题、正文、链接、元数据
- `krowork_scrape_elements` — 按 CSS 选择器提取元素
- `krowork_scrape_rss` — 解析 RSS/Atom 订阅源
- `krowork_scrape_table` — 提取 HTML 表格数据
- `krowork_scrape_api` — 调用 REST API 接口
- `krowork_monitor_page` — 监控网页内容变化
- `krowork_preprocess_content` — 预处理网页内容用于 AI 总结
</details>

<details>
<summary><strong>数据源 (4)</strong></summary>

- `krowork_register_datasource` — 注册 API/RSS/网页/文件/SQLite 数据源
- `krowork_list_datasources` — 列出已注册数据源
- `krowork_fetch_datasource` — 从数据源获取数据
- `krowork_delete_datasource` — 删除数据源
</details>

<details>
<summary><strong>导出导入 (2)</strong></summary>

- `krowork_export_app` — 打包应用为 `.krowork` 归档文件
- `krowork_import_app` — 从归档文件导入应用
</details>

<details>
<summary><strong>定时任务 (3)</strong></summary>

- `krowork_create_schedule` — 定时运行（每天/每周/间隔）
- `krowork_list_schedules` — 列出所有定时任务
- `krowork_delete_schedule` — 删除定时任务
</details>

<details>
<summary><strong>跨设备同步 (5)</strong></summary>

- `krowork_sync_configure` — 配置同步目录（OneDrive/坚果云等）
- `krowork_sync_push` — 推送本地应用到云端
- `krowork_sync_pull` — 从云端拉取应用
- `krowork_sync_status` — 查看同步状态
- `krowork_sync_list_remote` — 列出云端应用
</details>

<details>
<summary><strong>自动改进 (2)</strong></summary>

- `krowork_auto_improve` — 一键自动改进应用
- `krowork_list_improvements` — 列出可用的改进项
</details>

### 11 个斜杠命令

| 命令 | 功能 |
|---|---|
| `/krowork:create` | 从自然语言创建应用 |
| `/krowork:list` | 查看所有应用 |
| `/krowork:run` | 运行应用 |
| `/krowork:improve` | 改进应用（自动 + 手动） |
| `/krowork:delete` | 删除应用 |
| `/krowork:scrape` | 抓取网页内容 |
| `/krowork:datasource` | 管理数据源 |
| `/krowork:summarize` | AI 驱动的网页内容总结 |
| `/krowork:share` | 导出/导入应用 |
| `/krowork:schedule` | 定时任务调度 |
| `/krowork:sync` | 跨设备同步 |

### 自动改进：一句话搞定 8 种改动

| 类型 | 指令示例 |
|---|---|
| 添加字段 | `"加一个标签字段"` |
| 添加导出 | `"添加CSV导出"` / `"添加Markdown导出"` |
| 添加搜索 | `"加一个搜索框"` |
| 添加排序 | `"添加按时间排序"` |
| 更换主题 | `"换成绿色主题"` / `"切换为浅色模式"` |
| 定时运行 | `"每天早上8点自动运行"` |
| 关键词高亮 | `"AI相关内容标红高亮"` |
| 增加数据源 | `"增加API数据源"` |

---

## 快速开始

### 环境要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI 已安装
- Python 3.9+

### 安装

```bash
git clone https://github.com/YOUR_USERNAME/open-krowork.git
cd open-krowork

# 安装 Python 依赖（仅 3 个包）
pip install -r requirements.txt
```

### 使用方式 1：Plugin 模式（推荐）

```bash
claude --plugin-dir /path/to/open-krowork
```

`--plugin-dir` 会自动加载 `.claude-plugin/plugin.json` 并注册 MCP 服务器。

**可用功能：**

| 功能 | 是否可用 |
|---|---|
| 斜杠命令（`/krowork:create`、`/krowork:run` 等） | 可用 |
| MCP 工具（Claude 自动调用） | 可用 |
| Skills 引导流程（分步引导） | 可用 |

**使用方式：** 直接输入 `/krowork:create`、`/krowork:list`、`/krowork:run` 等斜杠命令。

### 使用方式 2：MCP Server 模式（全局）

如果你希望在**任意目录**启动 Claude Code 都能使用 KroWork：

```bash
# 一次性注册：
claude mcp add krowork -s user -- python /path/to/open-krowork/server/main.py

# 之后直接 `claude` 即可，不限目录：
claude
```

**可用功能：**

| 功能 | 是否可用 |
|---|---|
| 斜杠命令（`/krowork:create` 等） | 不可用 |
| MCP 工具（Claude 自动调用） | 可用 |
| Skills 引导流程 | 不可用 |

**使用方式：** 没有斜杠命令，直接用自然语言描述需求，Claude 会自动调用对应工具。示例：

```
你: 帮我创建一个书签管理应用，支持标签分类
Claude: [自动调用 krowork_create_app("bookmark-manager", "书签管理器 - ...")]

你: 列出我所有的应用
Claude: [自动调用 krowork_list_apps]

你: 运行 bookmark-manager
Claude: [自动调用 krowork_run_app("bookmark-manager")]
```

运行 `claude mcp list` 验证。两种模式可以共存。

**依赖清单**（仅 3 个）：

| 包名 | 版本 | 用途 |
|---|---|---|
| `requests` | >=2.28 | 网页抓取、数据源、API 调用 |
| `beautifulsoup4` | >=4.11 | HTML 解析、网页抓取 |
| `Pillow` | >=9.0 | 应用图标生成 |

重启 Claude Code 即可使用。运行 `claude mcp list` 可验证安装。

### 使用

```bash
# 启动 Claude Code
claude

# 创建你的第一个应用
> /krowork:create "书签管理器 - 收藏和整理网页书签，支持标签分类"

# 运行
> /krowork:run bookmark-manager

# 改进
> /krowork:improve bookmark-manager "添加搜索和CSV导出"

# 现在双击桌面快捷方式 — 你的应用独立运行，不再需要 Claude！
```

---

## 架构

```
open-krowork/
├── requirements.txt          # Python 依赖（3 个包）
├── install.sh                # 一键安装（macOS/Linux）
├── install.bat               # 一键安装（Windows）
├── settings.json             # 用户设置
├── hooks/
│   └── hooks.json            # 生命周期钩子
├── server/                   # 核心引擎（通过 claude mcp add 注册）
│   ├── main.py              # MCP 服务器（33个工具，stdio传输）
│   ├── app_manager.py       # 应用管理 + 桌面快捷方式
│   ├── code_generator.py    # 自动代码生成（3种模板）
│   ├── auto_improve.py      # 结构化自动改进
│   ├── sandbox.py           # 沙箱进程运行器
│   ├── scraper.py           # 网页抓取（10个函数）
│   ├── datasource.py        # 数据源注册（5种类型）
│   ├── app_export.py        # 导出/导入（.krowork归档）
│   ├── scheduler.py         # 系统级定时任务
│   ├── sync.py              # 跨设备同步
│   └── icon_generator.py    # 应用图标生成
└── skills/                  # 11个斜杠命令
    ├── create/
    ├── improve/
    ├── scrape/
    ├── summarize/
    ├── sync/
    └── ...
```

### 工作流程

```
自然语言描述
    ↓
AI 分析意图（CRUD / 仪表盘 / 工具）
    ↓
生成 Flask 后端 + 暗色主题 HTML 前端
    ↓
创建虚拟环境，安装依赖
    ↓
生成桌面快捷方式（.lnk / .desktop）
    ↓
用户双击图标 → 应用本地运行，零 Token 消耗
```

### 自动代码生成

代码生成器分析描述关键词，自动选择三种模板之一：

| 类型 | 触发关键词 | 生成内容 |
|---|---|---|
| **CRUD** | 通用数据管理 | 完整增删改查 API + 列表/添加/删除界面 |
| **仪表盘** | 股票/天气/新闻/监控 | 统计卡片 + Chart.js 图表 + 搜索 |
| **工具** | 生成器/转换/计算 | 输入 → 处理 → 输出 + 历史记录 |

---

## 安全

- **本地优先**：所有代码在子进程沙箱中运行
- **零上传**：应用数据永不离开你的设备
- **权限确认**：破坏性操作需用户明确授权
- **环境隔离**：每个应用拥有独立的 Python 虚拟环境

---

## 路线图

- [x] Phase 1 — 核心闭环：插件框架、代码生成、应用生命周期
- [x] Phase 2 — 体验增强：网页抓取、桌面快捷方式、数据源集成
- [x] Phase 3 — 协作生态：导出导入、定时调度、更多模板
- [x] Phase 4 — 高级能力：跨设备同步、自动改进、内容分析
- [ ] Phase 5 — 社区生态：应用市场、团队协作、插件 API

---

## 贡献

欢迎贡献代码！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交改动 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

---

## License

本项目基于 MIT 协议开源 — 详见 [LICENSE](LICENSE) 文件。
