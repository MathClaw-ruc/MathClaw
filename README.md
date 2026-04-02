<p align="center">
  <br>
  <img src="logo.png" alt="MathClaw Logo" width="180">
  <br>
</p>

<h1 align="center">MathClaw</h1>

<p align="center">
  面向初高中数学学习场景的多模态智能学习助手
</p>

<p align="center">
  中文 &nbsp｜&nbsp <a href="README_EN.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%20--%203.13-3776AB">
  <img src="https://img.shields.io/badge/node.js-18%2B-339933">
  <img src="https://img.shields.io/badge/npm-9%2B-CB3837">
  <img src="https://img.shields.io/badge/license-Apache%202.0-2ea44f">
</p>

> ⭐ 如果你喜欢这个项目，请点击右上角的 "Star" 按钮支持我们。你的支持是我们前进的动力！

## 📝 简介

MathClaw 是一款面向初高中数学学习场景的多模态学习助手，支持图片、截图、PDF 和文本输入，围绕以下核心链路工作：

```
OCR → 求解与验证 → 薄弱点诊断 → 引导式讲解 → 变式题生成 → 学习记忆更新
```

当前仓库已内置一套适合首跑的默认配置：

- 默认模型提供商：`dashscope`
- 默认基座地址：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 默认模型：`qwen3-vl-plus`
- 默认视觉能力：开启
- 默认 QQ / 企业微信通道：关闭
- 默认 Tavily / Playwright / Filesystem MCP：关闭

首次部署通常只需要准备一个百炼 Qwen API Key，其余均为按需启用的增强项。

## ✨ 主要特性

- **📐 数学场景专项优化**：默认模型组合针对数学图片题进行首跑优化，开箱即用。
- **🖼️ 多模态输入支持**：支持图片、截图、PDF 和文本多种输入形式，适应真实做题场景。
- **🔗 完整学习链路**：从 OCR 识题到变式练习，覆盖数学学习的全流程闭环。
- **⚙️ 首跑门槛低**：默认配置已内置，首次部署通常只需补充 `api_key` 即可启动。
- **🚀 启动路径清晰**：提供 `start.sh`，可同时启动后端和前端，一键拉起服务。
- **🔌 配置接口直接可用**：通过 `GET /api/config/template` 和 `POST /api/config/quickstart` 完成首轮配置。
- **📁 运行目录集中**：配置、密钥和日志默认写入仓库内部目录，便于排查和迁移。

## 🛠️ 环境准备

**推荐环境：**

- Python `3.10` - `3.13`
- Node.js `18+`
- npm `9+`
- Linux 服务器或 Linux 容器
- 可访问所配置的模型 API

**可选能力的额外依赖：**

- Playwright MCP / Filesystem MCP：需要 `npx`
- Tavily 搜索增强：需要 `Tavily API Key`

建议使用隔离环境安装 Python 依赖，优先推荐 `venv`。

### 方式一：使用 `venv`（推荐）

```bash
cd /path/to/mathclaw
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .

cd console
npm install
```

重新打开终端后，需先重新激活环境：

```bash
cd /path/to/mathclaw
source .venv/bin/activate
```

若机器上没有 `python3` 命令，可显式指定 Python 可执行文件：

```bash
/root/miniconda3/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

### 方式二：使用 `conda`

```bash
cd /path/to/mathclaw
conda create -n mathclaw python=3.11 -y
conda activate mathclaw
python -m pip install -U pip
python -m pip install -e .

cd console
npm install
```

后续所有 Python 命令默认在激活该环境后执行。

## 🚀 快速开始

### 1. 启动服务

**使用 `venv`：**

```bash
cd /path/to/mathclaw
source .venv/bin/activate
bash start.sh
```

**使用 `conda`：**

```bash
cd /path/to/mathclaw
conda activate mathclaw
bash start.sh
```

启动后默认访问地址：

| 服务 | 地址 |
|------|------|
| 后端 | `http://127.0.0.1:6006` |
| 前端 | `http://127.0.0.1:6008` |

`start.sh` 会将运行目录固定到仓库内部：

| 目录 | 路径 |
|------|------|
| 工作目录 | `$REPO/.mathclaw` |
| 密钥目录 | `$REPO/.mathclaw.secret` |
| 日志目录 | `$REPO/.runtime` |

如果只需要启动后端：

```bash
cd /path/to/mathclaw
source .venv/bin/activate
python scripts/start_mathclaw6006.py
```

### 2. 验证服务

```bash
curl http://127.0.0.1:6006/api/health
curl http://127.0.0.1:6006/api/config/template
```

- `/api/health`：确认后端进程已正常启动
- `/api/config/template`：查看默认配置模板及 quickstart 支持的字段

### 3. 写入最小配置

如果只是想先把系统跑起来，通常只需提交一个 API Key：

```bash
curl -X POST http://127.0.0.1:6006/api/config/quickstart \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "<YOUR_DASHSCOPE_API_KEY>"
  }'
```

该请求将自动完成以下操作：

- 设置默认提供商为 `dashscope`，模型为 `qwen3-vl-plus`，并开启视觉能力
- 将配置写入 `.mathclaw/config.json` 和 `.mathclaw.secret/providers.json`
- 若 API Key 有效，后端将尝试热加载该模型

## ⚙️ 配置说明

### 最小必填配置

| 参数 | 说明 |
|------|------|
| `api_key` | 模型提供商的 API Key（唯一必填项）|

以下参数已内置默认值，无需手动填写：

| 参数 | 默认值 |
|------|--------|
| `provider` | `dashscope` |
| `base_url` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `model_name` | `qwen3-vl-plus` |
| `supports_vision` | `true` |

### 可选配置项

如需切换模型或调整视觉能力，可修改：`provider`、`base_url`、`model_name`、`supports_vision`。

### 通道配置

**企业微信：**

填写参数前，需先在企业微信工作台创建智能机器人：

1. 进入 **企业微信工作台 → 智能机器人 → 创建机器人**
2. 选择 **API 模式**并开启**长连接**
3. 复制生成的**机器人 ID** 和**密钥**，分别对应 `wecom_bot_id` 和 `wecom_secret`

| 参数 | 说明 |
|------|------|
| `wecom_bot_id` | 必填，机器人 ID |
| `wecom_secret` | 必填，机器人密钥 |
| `wecom_bot_prefix` | 可选，Bot 消息前缀 |
| `wecom_welcome_message` | 可选，Bot 欢迎语 |

**QQ：**

| 参数 | 说明 |
|------|------|
| `qq_app_id` | 必填 |
| `qq_client_secret` | 必填 |
| `qq_bot_prefix` | 可选 |

### 搜索增强配置

启用 Tavily 搜索增强需补充：`enable_tavily`、`tavily_api_key`。

## 📡 配置接口说明

后端提供两个适合首次部署时使用的配置接口：

| 接口 | 说明 |
|------|------|
| `GET /api/config/template` | 查看默认值、字段列表和可选模块 |
| `POST /api/config/quickstart` | 写入配置并尝试热加载模型 |

### 常见配置示例

<details><summary><b>百炼 Qwen + 企业微信 + Tavily 搜索 ✅ 推荐</b></summary>

```bash
curl -X POST http://127.0.0.1:6006/api/config/quickstart \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "dashscope",
    "api_key": "<YOUR_DASHSCOPE_API_KEY>",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model_name": "qwen3-vl-plus",
    "supports_vision": true,
    "wecom_enabled": true,
    "wecom_bot_id": "<YOUR_WECOM_BOT_ID>",
    "wecom_secret": "<YOUR_WECOM_SECRET>",
    "wecom_bot_prefix": "",
    "wecom_welcome_message": "你好，我是 MathClaw。",
    "enable_tavily": true,
    "tavily_api_key": "<YOUR_TAVILY_API_KEY>"
  }'
```

</details>

<details><summary><b>百炼 Qwen + QQ</b></summary>

```bash
curl -X POST http://127.0.0.1:6006/api/config/quickstart \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "<YOUR_DASHSCOPE_API_KEY>",
    "qq_enabled": true,
    "qq_app_id": "<YOUR_QQ_APP_ID>",
    "qq_client_secret": "<YOUR_QQ_CLIENT_SECRET>",
    "qq_bot_prefix": ""
  }'
```

</details>

<details><summary><b>百炼 Qwen + Tavily 搜索</b></summary>

```bash
curl -X POST http://127.0.0.1:6006/api/config/quickstart \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "<YOUR_DASHSCOPE_API_KEY>",
    "enable_tavily": true,
    "tavily_api_key": "<YOUR_TAVILY_API_KEY>"
  }'
```

</details>

<details><summary><b>一次性提交完整配置</b></summary>

```bash
curl -X POST http://127.0.0.1:6006/api/config/quickstart \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "dashscope",
    "api_key": "<YOUR_DASHSCOPE_API_KEY>",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model_name": "qwen3-vl-plus",
    "supports_vision": true,
    "wecom_enabled": true,
    "wecom_bot_id": "<YOUR_WECOM_BOT_ID>",
    "wecom_secret": "<YOUR_WECOM_SECRET>",
    "wecom_bot_prefix": "",
    "wecom_welcome_message": "你好，我是 MathClaw。",
    "enable_tavily": true,
    "tavily_api_key": "<YOUR_TAVILY_API_KEY>"
  }'
```

> 建议尽量一次性提交完整配置，避免多次调用时后一次覆盖前一次的开关状态。

</details>

## ✅ 验证配置是否生效

`POST /api/config/quickstart` 返回值中的关键字段：

| 字段 | 含义 |
|------|------|
| `runner_started` | 模型是否已成功热加载 |
| `restart_required` | 是否需要重启后端以让通道或 MCP 生效 |
| `missing_required` | 当前缺少的关键参数 |
| `summary` | 当前配置摘要（不回显密钥）|

- `runner_started=true`：模型已可用，可直接进行文本或图片问答
- `restart_required=true`：已修改 QQ、企业微信或 MCP 配置，建议重启一次后端
- `missing_required` 非空：配置不完整，需继续补充参数

## 🔍 进一步验证

配置完成后，可通过以下接口进一步检查服务状态：

```bash
curl http://127.0.0.1:6006/api/config/model
curl http://127.0.0.1:6006/api/providers
```

浏览器直接访问前端界面：

```
http://127.0.0.1:6008
```

若在云主机上运行，将 `6006` 和 `6008` 端口映射到公网即可。

## 📁 运行后的常见文件

| 文件路径 | 说明 |
|----------|------|
| `./.mathclaw/config.json` | 主配置文件 |
| `./.mathclaw.secret/providers.json` | 模型提供商配置 |
| `./.runtime/mathclaw6006-live.log` | 后端日志 |
| `./.runtime/console6008-live.log` | 前端日志 |



## ℹ️ 补充说明

- 当前代码虽然已转向数学学习场景，但仓库中仍保留了部分历史 `research` 命名和论文相关模块，不影响数学主链路运行。
- 文档中如提到 `NanoBot`，仅用于说明 QQ 和企业微信的注册思路；实际字段以 MathClaw 当前代码为准。

## 🙏 致谢
 
MathClaw 的开发离不开以下优秀开源项目的支持与启发：
 
- [**ResearchClaw**](https://github.com/HKUDS/ResearchClaw)：MathClaw 的前身，提供了核心架构与早期实现基础。
- [**nanobot**](https://github.com/HKUDS/nanobot)：超轻量级 AI 助手框架，企业微信和 QQ 通道的接入思路参考自该项目。
 
## 📄 许可证
 
Copyright 2025-2026 MathClaw Contributors
 
本项目基于 [Apache License 2.0](LICENSE) 开源。