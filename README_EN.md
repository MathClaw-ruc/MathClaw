<div align="center">

<img src="logo.png" alt="MathClaw Logo" width="148" />

# MathClaw

**A multi-channel AI learning assistant for junior and senior high school mathematics**

MathClaw combines a tutoring workspace, study planning, memory graphs, scheduled summaries, and channel integrations in one workflow.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Console](https://img.shields.io/badge/Console-Student%20%26%20Admin-6C63FF?style=flat-square)](#console-modules)
[![Channels](https://img.shields.io/badge/Channels-WeCom%20%7C%20QQ%20%7C%20Feishu%20%7C%20More-00BFA6?style=flat-square)](#channels-and-integrations)
[![Memory](https://img.shields.io/badge/Memory-Knowledge%20%26%20Error%20Graphs-4F8EF7?style=flat-square)](#what-ships-today)
[![License](https://img.shields.io/badge/License-MIT-2EA44F?style=flat-square)](LICENSE)

[中文](README.md) · [English](README_EN.md) · [Quick Start](#quick-start) · [Core Modules](#core-modules) · [Console Modules](#console-modules) · [Communication](COMMUNICATION.md)

</div>

---

## What This Repository Is

This repository is the current, runnable MathClaw version. It no longer matches the older README that mentioned `start.sh`, quickstart config APIs, or the old React/FastAPI stack.

Today, MathClaw is:

- a **math tutoring agent** built on top of the `nanobot` runtime
- a customized **MathClaw console** with both student-facing and operator-facing pages
- a learning workflow centered on **study plans, heartbeat tasks, structured memory, knowledge graphs, and error graphs**
- a **multi-channel gateway** that can connect to WeCom, QQ, Feishu, Telegram, Slack, WhatsApp, and more

## What Ships Today

| Module | Current capability | Main code |
| --- | --- | --- |
| Chat Workspace | Single-thread tutoring workspace with text, image, and PDF upload; Markdown/table rendering | `console/main.js` · `console/serve.py` |
| Study Plan | Daily status, weekly plan, tomorrow suggestions, focus topics, and correction directions | `nanobot/agent/memory.py` · `workspace/cron/jobs.json` |
| Memory Graphs | Knowledge graph + error graph, focus/overview modes, node details, node deletion | `workspace/memory/graphs/*` · `console/main.js` |
| Heartbeat & Summaries | Daily summary, weekly summary, scheduled jobs, `HEARTBEAT.md` wake-up execution | `nanobot/cron/service.py` · `nanobot/heartbeat/service.py` |
| Multi-channel Gateway | Channel intake, routing, streaming coalescing, outbound retry | `nanobot/channels/manager.py` · `nanobot/cli/commands.py` |
| Models & Tools | Multi-provider routing, Web Search/Web Fetch, filesystem tools, shell, cron, message send-back, MCP, subagents | `nanobot/providers/registry.py` · `nanobot/agent/loop.py` |
| Custom Output Skills | Optional follow-up output boxes after attachment replies | `nanobot/agent/custom_output_skills.py` |
| Sessions & Memory | JSONL session persistence, daily memory, weekly summaries, graph snapshots | `nanobot/session/manager.py` · `nanobot/agent/memory.py` |

## Key Features

<table>
  <tr>
    <td width="25%">
      <strong>Math-first tutoring workflow</strong><br/>
      Built for secondary-school mathematics, with guided explanations, weakness analysis, and correction-oriented feedback.
    </td>
    <td width="25%">
      <strong>Student + operator console</strong><br/>
      One console includes both the student workspace and the management surfaces for runtime, channels, models, and heartbeat.
    </td>
    <td width="25%">
      <strong>Unified channel gateway</strong><br/>
      Connect the same MathClaw agent to multiple messaging platforms and route everything through one backend.
    </td>
    <td width="25%">
      <strong>Extensible toolchain</strong><br/>
      Filesystem, web, shell, cron, MCP, and channel plugins are all part of the current runtime.
    </td>
  </tr>
</table>

## Showcase

<table>
  <tr>
    <td width="33%" align="center">
      <img src="case/search.gif" alt="Chat Workspace" />
      <br />
      <strong>Chat workspace</strong>
      <br />
      Text / image / PDF input with structured answers
    </td>
    <td width="33%" align="center">
      <img src="case/scedule.gif" alt="Study Plan" />
      <br />
      <strong>Study plan + scheduled summaries</strong>
      <br />
      Daily rhythm, weekly planning, heartbeat-driven updates
    </td>
    <td width="33%" align="center">
      <img src="case/memory.gif" alt="Memory Graphs" />
      <br />
      <strong>Knowledge + error graphs</strong>
      <br />
      Visual memory for revision priorities and recurring mistakes
    </td>
  </tr>
</table>

<a id="core-modules"></a>

## Core Modules

<details>
<summary><b>🧠 Chat Workspace</b></summary>
<br />
<table>
  <tr>
    <td width="46%" align="center" valign="top">
      <img src="case/search.gif" alt="MathClaw Chat Workspace" width="100%" />
    </td>
    <td width="54%" valign="top">

- A single-thread math tutoring workspace for students
- Supports text, image, screenshot, and PDF input
- Answer area renders Markdown, lists, code blocks, and tables
- Follow-up conversation no longer depends on the old multi-session history UI
- Attachment replies can be extended with custom output skills such as a “competition coach” box

    </td>
  </tr>
</table>
</details>

<hr />

<details>
<summary><b>🗓️ Study Plan</b></summary>
<br />
<table>
  <tr>
    <td width="46%" align="center" valign="top">
      <img src="case/scedule.gif" alt="MathClaw Study Plan" width="100%" />
    </td>
    <td width="54%" valign="top">

- Automatically summarizes daily status, weekly plan, and tomorrow suggestions
- Pulls revision priorities and correction directions from structured learning memory
- Presents daily themes and practice dosage in a student-facing layout
- Designed as a study cockpit rather than an admin report

    </td>
  </tr>
</table>
</details>

<hr />

<details>
<summary><b>🕸️ Knowledge Graphs and Error Graphs</b></summary>
<br />
<table>
  <tr>
    <td width="46%" align="center" valign="top">
      <img src="case/memory.gif" alt="MathClaw Memory Graphs" width="100%" />
    </td>
    <td width="54%" valign="top">

- Maintains both a knowledge graph and an error graph
- Supports focus/overview modes, node highlighting, relation legends, and detail panels
- Knowledge graphs emphasize prerequisites, similarity, containment, and relation links
- Error graphs emphasize mistake patterns, recurrence, correction suggestions, and risk
- Node details support deletion for curation by teachers or operators

    </td>
  </tr>
</table>
</details>

<hr />

<details>
<summary><b>⏰ Scheduled Summaries and Heartbeat</b></summary>
<br />

- The workspace ships with `MathClaw Daily Summary` and `MathClaw Weekly Summary`
- `HEARTBEAT.md` is checked periodically for persistent tasks, not one-off reminders
- `cron/jobs.json` stores schedules, next/last execution times, and recent results
- The console includes a dedicated heartbeat page for rhythm, status, and troubleshooting

</details>

<hr />

<details>
<summary><b>📡 Multi-Channel Gateway</b></summary>
<br />

- Built-in channels include WeCom, QQ, Feishu, Telegram, Slack, Email, Discord, Matrix, Weixin, DingTalk, WhatsApp, and MoChat
- `nanobot gateway` handles channel startup, inbound routing, streaming coalescing, and outbound retry
- Runtime flags can override channel config directly for deployment and debugging
- External channel plugins are supported via Python entry points

</details>

<hr />

<details>
<summary><b>🛠️ Models, Tools, and MCP</b></summary>
<br />

- The provider registry already includes DashScope, OpenAI, Anthropic, DeepSeek, Gemini, OpenRouter, Ollama, and more
- Default tools include filesystem, shell, web search, web fetch, cron, message send-back, subagents, and MCP
- The console exposes the current model chain, context window, tool summary, and workspace boundaries
- This makes it practical to manage tutoring and operations inside one system

</details>

<hr />

<details>
<summary><b>✨ Custom Output Skills</b></summary>
<br />

- Adds an optional second response box after attachment-based replies
- Skills are stored in `workspace/custom_output_skills.json`
- The current repository supports create / enable / disable / delete flows from the console
- Useful for styles such as “competition coach hints”, “exam rubric reminders”, or “final-check prompts”

</details>

## Architecture

```mermaid
flowchart LR
    A["Student / Teacher / Operator"] --> B["Channels<br/>WeCom / QQ / Feishu / ..."]
    B --> C["nanobot gateway"]
    C --> D["MathClaw AgentLoop"]

    D --> E["LLM Providers<br/>DashScope / OpenAI / Anthropic / ..."]
    D --> F["Tools<br/>Web · Filesystem · Shell · Cron · MCP"]
    D --> G["Sessions<br/>JSONL conversation history"]
    D --> H["Memory Runtime<br/>Daily / Weekly / Graphs"]
    D --> I["Heartbeat / Cron"]

    H --> J["Study Plan page"]
    H --> K["Memory Graph page"]
    I --> L["Heartbeat page"]
    C --> M["MathClaw Console"]
```

## Console Modules

| Page | Audience | Current purpose |
| --- | --- | --- |
| Chat Workspace | Student | Single-thread tutoring workspace with attachment upload and rich Markdown answers |
| Study Plan | Student | Daily status, weekly plan, tomorrow suggestions, focus topics, practice load |
| Memory | Student / Teacher | Knowledge graph, error graph, node details, relation browsing |
| Runtime Status | Operator | Health summary, model chain, tool abilities, active channels, attachment pipeline |
| Channels | Operator | Per-channel enablement, daily message count, active sessions, last activity |
| Heartbeat | Operator | Scheduled summaries, heartbeat rhythm, latest result, troubleshooting order |
| Skills | Operator | Manage custom output skills used after attachment replies |
| MCP / Agent Config / Models | Operator | View current tools, agent boundaries, and model chain |

## Quick Start

### 1. Requirements

- Python `3.11+`
- Linux / macOS / WSL recommended for deployment
- a usable model API key
- optional: Node.js `20+` only if you need the WhatsApp bridge

### 2. Install

```bash
git clone https://github.com/MathClaw-ruc/MathClaw.git
cd MathClaw

python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

If you need WeCom support:

```bash
python -m pip install -e ".[wecom]"
```

### 3. Initialize config and workspace

```bash
nanobot onboard --workspace ./workspace
```

This creates:

- config: `~/.nanobot/config.json`
- workspace templates: `./workspace/AGENTS.md`, `USER.md`, `HEARTBEAT.md`, `cron/jobs.json`

Interactive setup is also available:

```bash
nanobot onboard --workspace ./workspace --wizard
```

### 4. Minimal config example

```json
{
  "agents": {
    "defaults": {
      "workspace": "/path/to/MathClaw/workspace",
      "model": "qwen3.5-plus",
      "provider": "dashscope",
      "timezone": "Asia/Shanghai"
    }
  },
  "providers": {
    "dashscope": {
      "api_key": "YOUR_DASHSCOPE_API_KEY"
    }
  },
  "tools": {
    "web": {
      "search": {
        "provider": "tavily",
        "api_key": "YOUR_TAVILY_API_KEY"
      }
    }
  }
}
```

### 5. Start the gateway

```bash
nanobot gateway --workspace ./workspace
```

Default gateway port: `18790`

### 6. Start the console

```bash
cd console
NANOBOT_CONSOLE_WORKSPACE=../workspace python serve.py
```

Default console address:

```text
http://127.0.0.1:6006
```

If you want to use port `6008` instead:

```bash
cd console
NANOBOT_CONSOLE_WORKSPACE=../workspace NANOBOT_CONSOLE_PORT=6008 python serve.py
```

### 7. Talk to the agent from CLI

```bash
nanobot agent --workspace ./workspace -m "Teach me monotonicity from derivatives"
```

## Channels and Integrations

### Built-in channels

The current repository includes built-in modules for:

- WeCom
- QQ
- Feishu
- Telegram
- Slack
- Email
- Discord
- Matrix
- Weixin
- DingTalk
- WhatsApp
- MoChat

It also supports external channel plugins via Python entry points. See [docs/CHANNEL_PLUGIN_GUIDE.md](docs/CHANNEL_PLUGIN_GUIDE.md).

### Runtime override examples

WeCom:

```bash
nanobot gateway --workspace ./workspace \
  --wecom \
  --wecom-bot-id YOUR_WECOM_BOT_ID \
  --wecom-secret YOUR_WECOM_SECRET \
  --wecom-allow-from "*"
```

QQ:

```bash
nanobot gateway --workspace ./workspace \
  --qq \
  --qq-app-id YOUR_QQ_APP_ID \
  --qq-secret YOUR_QQ_SECRET \
  --qq-allow-from "*"
```

Feishu:

```bash
nanobot gateway --workspace ./workspace \
  --feishu \
  --feishu-app-id YOUR_FEISHU_APP_ID \
  --feishu-app-secret YOUR_FEISHU_APP_SECRET \
  --feishu-allow-from "*"
```

For channels that require interactive auth:

```bash
nanobot channels login <channel_name>
```

To inspect channel status:

```bash
nanobot channels status
```

## Providers and Tools

### Supported providers

The current provider registry already includes:

- DashScope
- OpenAI
- Anthropic
- DeepSeek
- Gemini
- OpenRouter
- Azure OpenAI
- Zhipu AI
- Moonshot
- MiniMax
- Mistral
- Step Fun
- Groq
- Ollama
- vLLM
- OpenVINO Model Server
- OpenAI Codex
- GitHub Copilot
- custom OpenAI-compatible endpoints

### Default agent tools

`AgentLoop` currently registers:

- file read / write / edit / list
- shell execution
- web search / web fetch
- outbound message tool
- subagent spawn
- cron scheduling
- MCP tool servers

## Learning Memory and Automation

What makes this repository distinctive is not just chat. It continuously turns tutoring activity into reusable learning memory:

- daily learning memory
- weekly summaries
- knowledge graphs
- error graphs
- tomorrow suggestions
- heartbeat tasks
- persisted cron schedules

Relevant workspace files:

- `workspace/HEARTBEAT.md`
- `workspace/cron/jobs.json`
- `workspace/custom_output_skills.json`
- `workspace/memory/graphs/knowledge_graph.json`
- `workspace/memory/graphs/error_graph.json`

## Repository Structure

```text
.
├── nanobot/                 # Core runtime: agent, channels, providers, memory, cron, heartbeat
├── console/                 # MathClaw console: static frontend shell + serve.py API layer
├── workspace/               # Repo-owned MathClaw persona, plans, and templates
├── bridge/                  # WhatsApp bridge (Node 20+)
├── case/                    # GIF demos used in the README
├── docs/                    # Docs such as the channel plugin guide
└── tests/                   # Runtime, tool, security, and channel tests
```

## README Scope

This README has been rewritten against the current codebase and is intentionally aligned with:

- `nanobot gateway`
- `nanobot agent`
- `console/serve.py`
- `workspace/*`
- `nanobot/agent/*`

It does not describe the old quickstart APIs, old startup scripts, or the previous frontend/backend stack.

## License

This project is released under the [MIT License](LICENSE).
