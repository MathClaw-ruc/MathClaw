<p align="center">
  <br>
  <img src="logo.png" alt="MathClaw Logo" width="180">
  <br>
</p>

<h1 align="center">MathClaw</h1>

<p align="center">
  A Multimodal Learning Assistant for Middle and High School Mathematics
</p>

<p align="center">
  <a href="README.md">中文</a> &nbsp｜&nbsp English
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%20--%203.13-3776AB">
  <img src="https://img.shields.io/badge/node.js-18%2B-339933">
  <img src="https://img.shields.io/badge/npm-9%2B-CB3837">
  <img src="https://img.shields.io/badge/license-Apache%202.0-2ea44f">
</p>

> ⭐ If you find this project helpful, please click the "Star" button in the top right corner. Your support means a lot!

## 📝 Introduction

MathClaw is a multimodal learning assistant designed for middle and high school mathematics. It supports image, screenshot, PDF, and text input, and operates around the following core pipeline:

```
OCR → Solving & Verification → Weakness Diagnosis → Guided Explanation → Variant Problem Generation → Learning Memory Update
```

The repository ships with a set of ready-to-run defaults:

- Default model provider: `dashscope`
- Default base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Default model: `qwen3-vl-plus`
- Default vision support: enabled
- Default QQ / WeCom channel: disabled
- Default Tavily / Playwright / Filesystem MCP: disabled

For a first deployment, you typically only need a DashScope Qwen API Key. Everything else is opt-in.

## ✨ Key Features

- **📐 Math-Optimized Out of the Box**: Default model combination is tuned for math image problems — works immediately after setup.
- **🖼️ Multimodal Input**: Supports images, screenshots, PDFs, and plain text to cover real-world problem-solving scenarios.
- **🔗 Full Learning Pipeline**: From OCR recognition to variant practice problems, covering the complete math learning loop.
- **⚙️ Low Setup Barrier**: Built-in defaults mean first deployment usually only requires adding an `api_key`.
- **🚀 Clear Startup Path**: `start.sh` launches both backend and frontend in one command.
- **🔌 Config API Ready**: Use `GET /api/config/template` and `POST /api/config/quickstart` to configure on first run.
- **📁 Centralized Runtime Directory**: Config, secrets, and logs are written inside the repo directory for easy inspection and migration.

## 🛠️ Requirements

**Recommended environment:**

- Python `3.10` - `3.13`
- Node.js `18+`
- npm `9+`
- Linux server or Linux container
- Access to your configured model API

**Additional dependencies for optional features:**

- Playwright MCP / Filesystem MCP: requires `npx`
- Tavily search enhancement: requires a `Tavily API Key`

We recommend using an isolated Python environment. `venv` is preferred.

### Option 1: Using `venv` (Recommended)

```bash
cd /path/to/mathclaw
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .

cd console
npm install
```

After reopening a terminal, re-activate the environment first:

```bash
cd /path/to/mathclaw
source .venv/bin/activate
```

If `python3` is not available, specify the Python executable explicitly:

```bash
/root/miniconda3/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

### Option 2: Using `conda`

```bash
cd /path/to/mathclaw
conda create -n mathclaw python=3.11 -y
conda activate mathclaw
python -m pip install -U pip
python -m pip install -e .

cd console
npm install
```

All subsequent Python commands assume this environment is active.

## 🚀 Quick Start

### 1. Start the Service

**Using `venv`:**

```bash
cd /path/to/mathclaw
source .venv/bin/activate
bash start.sh
```

**Using `conda`:**

```bash
cd /path/to/mathclaw
conda activate mathclaw
bash start.sh
```

Default addresses after startup:

| Service | Address |
|---------|---------|
| Backend | `http://127.0.0.1:6006` |
| Frontend | `http://127.0.0.1:6008` |

`start.sh` pins the runtime directories inside the repo:

| Directory | Path |
|-----------|------|
| Working directory | `$REPO/.mathclaw` |
| Secrets directory | `$REPO/.mathclaw.secret` |
| Log directory | `$REPO/.runtime` |

To start the backend only:

```bash
cd /path/to/mathclaw
source .venv/bin/activate
python scripts/start_mathclaw6006.py
```

### 2. Verify the Service

```bash
curl http://127.0.0.1:6006/api/health
curl http://127.0.0.1:6006/api/config/template
```

- `/api/health`: Confirms the backend process is running
- `/api/config/template`: Shows the default config template and fields supported by quickstart

### 3. Write Minimal Config

To get the system running, just submit an API Key:

```bash
curl -X POST http://127.0.0.1:6006/api/config/quickstart \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "<YOUR_DASHSCOPE_API_KEY>"
  }'
```

This request will automatically:

- Set the default provider to `dashscope`, model to `qwen3-vl-plus`, and enable vision support
- Write config to `.mathclaw/config.json` and `.mathclaw.secret/providers.json`
- Attempt to hot-load the model if the API Key is valid

## ⚙️ Configuration

### Minimum Required Config

| Parameter | Description |
|-----------|-------------|
| `api_key` | Model provider API Key (the only required field) |

The following parameters have built-in defaults and do not need to be set manually:

| Parameter | Default |
|-----------|---------|
| `provider` | `dashscope` |
| `base_url` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `model_name` | `qwen3-vl-plus` |
| `supports_vision` | `true` |

### Optional Parameters

To switch models or adjust vision support, modify: `provider`, `base_url`, `model_name`, `supports_vision`.

### Channel Configuration

**WeCom (企业微信):**

Before filling in the parameters, create an AI bot in the WeCom admin console:

1. Go to **WeCom Admin Console → AI Bots → Create Bot**
2. Select **API mode** and enable **persistent connection**
3. Copy the generated **Bot ID** and **Secret**, corresponding to `wecom_bot_id` and `wecom_secret`

| Parameter | Description |
|-----------|-------------|
| `wecom_bot_id` | Required, Bot ID |
| `wecom_secret` | Required, Bot Secret |
| `wecom_bot_prefix` | Optional, bot message prefix |
| `wecom_welcome_message` | Optional, bot welcome message |

**QQ:**

| Parameter | Description |
|-----------|-------------|
| `qq_app_id` | Required |
| `qq_client_secret` | Required |
| `qq_bot_prefix` | Optional |

### Search Enhancement

To enable Tavily search, provide: `enable_tavily`, `tavily_api_key`.

## 📡 Config API

The backend provides two endpoints for first-time deployment:

| Endpoint | Description |
|----------|-------------|
| `GET /api/config/template` | View defaults, field list, and optional modules |
| `POST /api/config/quickstart` | Write config and attempt to hot-load the model |

### Configuration Examples

<details><summary><b>DashScope Qwen + WeCom + Tavily ✅ Recommended</b></summary>

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
    "wecom_welcome_message": "Hi, I am MathClaw.",
    "enable_tavily": true,
    "tavily_api_key": "<YOUR_TAVILY_API_KEY>"
  }'
```

</details>

<details><summary><b>DashScope Qwen + QQ</b></summary>

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

<details><summary><b>DashScope Qwen + Tavily Search</b></summary>

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

<details><summary><b>Full Config in One Request</b></summary>

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
    "wecom_welcome_message": "Hi, I am MathClaw.",
    "enable_tavily": true,
    "tavily_api_key": "<YOUR_TAVILY_API_KEY>"
  }'
```

> We recommend submitting the full config in a single request. Multiple calls may cause later submissions to overwrite earlier toggle states.

</details>

## ✅ Verifying Config

Key fields in the `POST /api/config/quickstart` response:

| Field | Meaning |
|-------|---------|
| `runner_started` | Whether the model was successfully hot-loaded |
| `restart_required` | Whether a backend restart is needed for channels or MCP to take effect |
| `missing_required` | Any required parameters still missing |
| `summary` | Current config summary (secrets are not echoed back) |

- `runner_started=true`: Model is ready, text and image Q&A can be tested immediately
- `restart_required=true`: QQ, WeCom, or MCP config was changed — restart the backend once
- `missing_required` non-empty: Config is incomplete, continue adding the missing parameters

## 🔍 Further Verification

After configuration, check service status with:

```bash
curl http://127.0.0.1:6006/api/config/model
curl http://127.0.0.1:6006/api/providers
```

Access the frontend directly in your browser:

```
http://127.0.0.1:6008
```

If running on a cloud server, expose ports `6006` and `6008` through your platform's port mapping.

## 📁 Runtime Files

| File Path | Description |
|-----------|-------------|
| `./.mathclaw/config.json` | Main config file |
| `./.mathclaw.secret/providers.json` | Model provider config |
| `./.runtime/mathclaw6006-live.log` | Backend log |
| `./.runtime/console6008-live.log` | Frontend log |

## ℹ️ Notes

- The codebase has shifted to math learning, but some historical `research` naming and paper-related modules remain in the repo. They do not affect the math pipeline.

## 🙏 Acknowledgements

MathClaw builds on the following open-source projects:

- [**ResearchClaw**](https://github.com/HKUDS/ResearchClaw): The predecessor of MathClaw, providing the core architecture and early implementation foundation.
- [**nanobot**](https://github.com/HKUDS/nanobot): An ultra-lightweight AI assistant framework. The WeCom and QQ channel integration approach is inspired by this project.

## 📄 License

Copyright 2025-2026 MathClaw Contributors

This project is licensed under the [Apache License 2.0](LICENSE).