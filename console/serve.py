from __future__ import annotations

import asyncio
import cgi
import json
import os
import re
import sys
import threading
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


HOST = os.environ.get("NANOBOT_CONSOLE_HOST", "127.0.0.1")
PORT = int(os.environ.get("NANOBOT_CONSOLE_PORT", "6006"))
ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
SESSION_KEY = os.environ.get("NANOBOT_CONSOLE_SESSION_KEY", "web:mathclaw-console")
CHAT_CHANNEL = os.environ.get("NANOBOT_CONSOLE_CHANNEL", "web")
CHAT_ID = os.environ.get("NANOBOT_CONSOLE_CHAT_ID", "mathclaw-console")
FALLBACK_CONFIG_PATH = Path(
    os.environ.get(
        "NANOBOT_CONSOLE_FALLBACK_CONFIG",
        "/root/autodl-tmp/MathClaw/.mathclaw/config.json",
    )
)
UPLOAD_DIR = ROOT / ".uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_LOG = UPLOAD_DIR / "events.jsonl"

sys.path.insert(0, str(REPO_ROOT))

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.cli.commands import _load_runtime_config, _make_provider
from nanobot.cron.service import CronService
from nanobot.utils.helpers import sync_workspace_templates


def build_runtime_config():
    workspace = os.environ.get("NANOBOT_CONSOLE_WORKSPACE")
    config = _load_runtime_config(None, workspace)

    fallback: dict[str, Any] = {}
    if FALLBACK_CONFIG_PATH.exists():
        fallback = json.loads(FALLBACK_CONFIG_PATH.read_text(encoding="utf-8"))

    model = (
        os.environ.get("NANOBOT_CONSOLE_MODEL")
        or os.environ.get("NANOBOT_AGENTS__DEFAULTS__MODEL")
        or fallback.get("model_name")
    )
    api_key = (
        os.environ.get("NANOBOT_CONSOLE_DASHSCOPE_API_KEY")
        or os.environ.get("NANOBOT_PROVIDERS__DASHSCOPE__API_KEY")
        or fallback.get("api_key")
    )
    api_base = (
        os.environ.get("NANOBOT_CONSOLE_DASHSCOPE_API_BASE")
        or os.environ.get("NANOBOT_PROVIDERS__DASHSCOPE__API_BASE")
        or fallback.get("base_url")
    )
    timezone = (
        os.environ.get("NANOBOT_CONSOLE_TIMEZONE")
        or os.environ.get("NANOBOT_AGENTS__DEFAULTS__TIMEZONE")
        or "Asia/Shanghai"
    )

    if model:
        config.agents.defaults.model = model
    config.agents.defaults.timezone = timezone

    if api_key:
        config.providers.dashscope.api_key = api_key
    if api_base:
        config.providers.dashscope.api_base = api_base

    if not config.get_provider(config.agents.defaults.model):
        raise RuntimeError("No usable provider configured for console chat.")

    return config


class ConsoleRuntime:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._request_lock = threading.Lock()
        self.agent: AgentLoop | None = None
        self.config = None
        future = asyncio.run_coroutine_threadsafe(self._startup(), self.loop)
        future.result(timeout=60)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _startup(self) -> None:
        config = build_runtime_config()
        self.config = config
        sync_workspace_templates(config.workspace_path)

        bus = MessageBus()
        provider = _make_provider(config)
        cron = CronService(config.workspace_path / "cron" / "jobs.json")

        self.agent = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=config.workspace_path,
            model=config.agents.defaults.model,
            max_iterations=config.agents.defaults.max_tool_iterations,
            context_window_tokens=config.agents.defaults.context_window_tokens,
            web_search_config=config.tools.web.search,
            web_proxy=config.tools.web.proxy or None,
            exec_config=config.tools.exec,
            cron_service=cron,
            restrict_to_workspace=config.tools.restrict_to_workspace,
            mcp_servers=config.tools.mcp_servers,
            timezone=config.agents.defaults.timezone,
        )

    async def _dashboard(self) -> dict[str, Any]:
        assert self.agent is not None
        graphs = await self._graphs()
        workspace = self.agent.workspace
        return {
            "student": self._build_student_payload(workspace, graphs),
            "admin": self._build_admin_payload(workspace),
        }

    async def _history(self) -> dict[str, Any]:
        assert self.agent is not None
        self.agent.sessions.invalidate(SESSION_KEY)
        session = self.agent.sessions.get_or_create(SESSION_KEY)
        return {"messages": self._serialize_messages(session.messages)}

    async def _send(self, content: str, media: list[str] | None = None) -> dict[str, Any]:
        assert self.agent is not None
        self.agent.sessions.invalidate(SESSION_KEY)
        await self.agent.process_direct(
            content,
            session_key=SESSION_KEY,
            channel=CHAT_CHANNEL,
            chat_id=CHAT_ID,
            media=media or None,
        )
        session = self.agent.sessions.get_or_create(SESSION_KEY)
        return {"messages": self._serialize_messages(session.messages)}

    async def _graphs(self) -> dict[str, Any]:
        assert self.agent is not None
        graph_dir = self.agent.workspace / "memory" / "graphs"
        return {
            "knowledge": self._read_graph_file(graph_dir / "knowledge_graph.json", "knowledge"),
            "error": self._read_graph_file(graph_dir / "error_graph.json", "error"),
        }

    async def _delete_graph_node(self, graph: str, node_id: str) -> dict[str, Any]:
        assert self.agent is not None
        self.agent.context.memory.delete_graph_node(graph, node_id)
        return await self._graphs()

    async def _list_custom_output_skills(self) -> dict[str, Any]:
        assert self.agent is not None
        store = self.agent.custom_output_skills
        return {
            "skills": store.list_dicts(),
            "limit": store.max_skills,
        }

    async def _create_custom_output_skill(self, requirement: str) -> dict[str, Any]:
        assert self.agent is not None
        store = self.agent.custom_output_skills
        skill = await store.create(requirement)
        return {
            "skill": skill.to_dict(),
            "skills": store.list_dicts(),
            "limit": store.max_skills,
        }

    async def _toggle_custom_output_skill(self, skill_id: str, enabled: bool) -> dict[str, Any]:
        assert self.agent is not None
        store = self.agent.custom_output_skills
        skill = store.set_enabled(skill_id, enabled)
        return {
            "skill": skill.to_dict(),
            "skills": store.list_dicts(),
            "limit": store.max_skills,
        }

    async def _delete_custom_output_skill(self, skill_id: str) -> dict[str, Any]:
        assert self.agent is not None
        store = self.agent.custom_output_skills
        store.delete(skill_id)
        return {
            "skills": store.list_dicts(),
            "limit": store.max_skills,
        }

    def _build_student_payload(self, workspace: Path, graphs: dict[str, Any]) -> dict[str, Any]:
        daily_json = self._load_latest_daily_json(workspace)
        weekly = self._load_latest_weekly_summary(workspace)
        knowledge_nodes = self._top_nodes(graphs.get("knowledge", {}), "knowledge")
        error_nodes = self._top_nodes(graphs.get("error", {}), "error")
        return {
            "daily": daily_json,
            "weekly": weekly,
            "highlights": {
                "focus": knowledge_nodes[:3],
                "mistakes": error_nodes[:3],
            },
        }

    def _build_admin_payload(self, workspace: Path) -> dict[str, Any]:
        assert self.agent is not None
        today_events = self._load_today_events(workspace)
        return {
            "runtime": self._runtime_snapshot(),
            "channels": self._channel_snapshots(workspace, today_events),
            "schedules": self._schedule_snapshots(workspace),
            "settings": self._settings_snapshot(),
        }

    def _runtime_snapshot(self) -> dict[str, Any]:
        assert self.agent is not None
        gateway_pid = self._read_pid(REPO_ROOT / ".runtime" / "gateway.pid")
        return {
            "gateway": {
                "pid": gateway_pid,
                "online": self._pid_alive(gateway_pid),
            },
            "console": {
                "pid": os.getpid(),
                "online": True,
            },
            "model": self.agent.model,
            "provider": "DashScope (OpenAI-compatible)",
            "doc_model": "qwen-doc-turbo",
            "image_pipeline": "原图 + Markdown 转写 + qwen3.5",
            "timezone": self.agent.context.timezone or "Asia/Shanghai",
            "custom_skill_count": len(self.agent.custom_output_skills.enabled()),
        }

    def _settings_snapshot(self) -> dict[str, Any]:
        assert self.agent is not None
        config = self.config
        runtime_channels = self._runtime_enabled_channels()
        return {
            "context_window_tokens": self.agent.context_window_tokens,
            "max_iterations": self.agent.max_iterations,
            "restrict_to_workspace": self.agent.restrict_to_workspace,
            "workspace": str(self.agent.workspace),
            "mcp_server_count": len(getattr(self.agent, "_mcp_servers", {}) or {}),
            "search_provider": getattr(self.agent.web_search_config, "provider", ""),
            "tools": self._tool_snapshots(),
            "safe_env_keys": [
                key
                for key in (
                    "NANOBOT_AGENTS__DEFAULTS__MODEL",
                    "NANOBOT_AGENTS__DEFAULTS__TIMEZONE",
                    "NANOBOT_TOOLS__WEB__SEARCH__PROVIDER",
                    "NANOBOT_PROVIDERS__DASHSCOPE__API_BASE",
                )
                if os.environ.get(key)
            ],
            "reply_channels": [
                channel
                for channel in ("wecom", "qq", "feishu", "web")
                if channel in runtime_channels
                or (
                    getattr(config.channels, channel, None)
                    and getattr(getattr(config.channels, channel), "enabled", False)
                )
            ] if config else [],
        }

    def _channel_snapshots(self, workspace: Path, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        assert self.config is not None
        runtime_channels = self._runtime_enabled_channels()
        known = {
            "wecom": "企业微信",
            "qq": "QQ",
            "feishu": "飞书",
            "web": "解题工作台",
        }
        by_channel: dict[str, dict[str, Any]] = {
            key: {
                "id": key,
                "label": label,
                "enabled": (
                    key == "web"
                    or key in runtime_channels
                    or bool(getattr(getattr(self.config.channels, key, None), "enabled", False))
                ),
                "messages_today": 0,
                "attachments_today": 0,
                "sessions_today": set(),
                "last_message_at": None,
            }
            for key, label in known.items()
        }
        for item in events:
            session_key = str(item.get("session_key", ""))
            channel = session_key.split(":", 1)[0] if ":" in session_key else "web"
            if channel not in by_channel:
                continue
            target = by_channel[channel]
            target["enabled"] = True
            target["messages_today"] += 1
            target["sessions_today"].add(session_key)
            timestamp = str(item.get("timestamp", ""))
            if timestamp and (not target["last_message_at"] or timestamp > target["last_message_at"]):
                target["last_message_at"] = timestamp
        for item in by_channel.values():
            if item["id"] == "web":
                item["attachments_today"] = self._web_uploads_today(workspace)
            else:
                item["attachments_today"] = self._session_attachment_turns_today(workspace, item["sessions_today"])
        snapshots: list[dict[str, Any]] = []
        for item in by_channel.values():
            snapshots.append(
                {
                    **item,
                    "sessions_today": len(item["sessions_today"]),
                }
            )
        return snapshots

    def _schedule_snapshots(self, workspace: Path) -> list[dict[str, Any]]:
        jobs_path = workspace / "cron" / "jobs.json"
        payload = self._read_json_file(jobs_path)
        jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
        snapshots = []
        for job in jobs:
            if not isinstance(job, dict):
                continue
            state = job.get("state", {}) if isinstance(job.get("state"), dict) else {}
            schedule = job.get("schedule", {}) if isinstance(job.get("schedule"), dict) else {}
            snapshots.append(
                {
                    "id": str(job.get("id", "")),
                    "name": str(job.get("name", "")),
                    "enabled": bool(job.get("enabled", False)),
                    "expr": str(schedule.get("expr", "")),
                    "timezone": str(schedule.get("tz", "Asia/Shanghai")),
                    "next_run": self._ms_to_iso(state.get("nextRunAtMs")),
                    "last_run": self._ms_to_iso(state.get("lastRunAtMs")),
                    "last_status": state.get("lastStatus"),
                }
            )
        return snapshots

    def _tool_snapshots(self) -> list[dict[str, str]]:
        assert self.agent is not None
        search_provider = getattr(self.agent.web_search_config, "provider", "") or "builtin"
        tools = [
            {
                "id": "web-search",
                "label": "网络搜索",
                "detail": f"{search_provider} 搜索链路",
            },
            {
                "id": "doc-reader",
                "label": "文档理解",
                "detail": "qwen-doc-turbo 先按问题提炼文档",
            },
            {
                "id": "image-reader",
                "label": "图片解析",
                "detail": "原图 + Markdown 转写 + qwen3.5",
            },
            {
                "id": "memory-context",
                "label": "学习记忆",
                "detail": "每日总结、每周计划和双图谱一起入上下文",
            },
            {
                "id": "custom-output",
                "label": "自定义输出框",
                "detail": f"当前启用 {len(self.agent.custom_output_skills.enabled())} 个附件风格输出",
            },
        ]
        mcp_count = len(getattr(self.agent, "_mcp_servers", {}) or {})
        if mcp_count:
            tools.append(
                {
                    "id": "mcp",
                    "label": "MCP 连接",
                    "detail": f"已连接 {mcp_count} 个外部工具服务器",
                }
            )
        return tools

    def _runtime_enabled_channels(self) -> set[str]:
        enabled = {"web"}
        gateway_pid = self._read_pid(REPO_ROOT / ".runtime" / "gateway.pid")
        cmdline = self._read_cmdline(gateway_pid)
        for flag, channel in (
            ("--wecom", "wecom"),
            ("--qq", "qq"),
            ("--feishu", "feishu"),
        ):
            if flag in cmdline:
                enabled.add(channel)
        return enabled

    def _session_attachment_turns_today(self, workspace: Path, session_keys: set[str]) -> int:
        total = 0
        today = datetime.now().date().isoformat()
        for session_key in session_keys:
            path = workspace / "sessions" / f"{session_key.replace(':', '_')}.jsonl"
            if not path.exists():
                continue
            for item in self._read_jsonl(path):
                if str(item.get("role", "")) != "user":
                    continue
                if not str(item.get("timestamp", "")).startswith(today):
                    continue
                if self._message_has_attachment(item.get("content")):
                    total += 1
        return total

    def _web_uploads_today(self, workspace: Path) -> int:
        fallback = max(self._web_session_attachment_markers_today(workspace), self._web_uploaded_files_today())
        if not UPLOAD_LOG.exists():
            return fallback
        today = datetime.now().date().isoformat()
        total = 0
        for item in self._read_jsonl(UPLOAD_LOG):
            if str(item.get("timestamp", "")).startswith(today):
                total += int(item.get("count", 0) or 0)
        return max(total, fallback)

    def _web_session_attachment_markers_today(self, workspace: Path) -> int:
        path = workspace / "sessions" / f"{SESSION_KEY.replace(':', '_')}.jsonl"
        if not path.exists():
            return 0
        today = datetime.now().date().isoformat()
        count = 0
        for item in self._read_jsonl(path):
            if not str(item.get("timestamp", "")).startswith(today):
                continue
            if str(item.get("role", "")) != "assistant":
                continue
            content = self._content_to_payload(item.get("content")).get("content", "")
            if "已收到附件" in content or "已解析图片内容" in content:
                count += 1
        return count

    @staticmethod
    def _web_uploaded_files_today() -> int:
        today = datetime.now().date()
        total = 0
        for path in UPLOAD_DIR.iterdir():
            if path == UPLOAD_LOG or not path.is_file():
                continue
            if datetime.fromtimestamp(path.stat().st_mtime).date() == today:
                total += 1
        return total

    @classmethod
    def _message_has_attachment(cls, content: Any) -> bool:
        if isinstance(content, str):
            markers = ("[image:", "[file:", "[voice", "[图片", "[附件")
            return any(marker in content for marker in markers)
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") in {"image_url", "input_image", "file", "input_file"}:
                    return True
        return False

    def _load_today_events(self, workspace: Path) -> list[dict[str, Any]]:
        today_dir = workspace / "memory" / "daily_conversations" / datetime.now().strftime("%Y.%-m.%-d")
        if not today_dir.exists():
            candidates = sorted((workspace / "memory" / "daily_conversations").glob("*/events.jsonl"))
            if not candidates:
                return []
            return self._read_jsonl(candidates[-1])
        return self._read_jsonl(today_dir / "events.jsonl")

    def _load_latest_daily_json(self, workspace: Path) -> dict[str, Any]:
        path = self._latest_file(workspace / "memory" / "daily_memory", ".json")
        payload = self._read_json_file(path)
        if not isinstance(payload, dict):
            return {
                "date": "",
                "learning_status_summary": "",
                "tomorrow_study_suggestions": [],
                "high_risk_knowledge_points": [],
                "high_frequency_error_types": [],
            }
        payload.setdefault("date", "")
        payload.setdefault("learning_status_summary", "")
        payload.setdefault("tomorrow_study_suggestions", [])
        payload.setdefault("high_risk_knowledge_points", [])
        payload.setdefault("high_frequency_error_types", [])
        payload["learning_status_summary"] = self._clean_markdown_text(payload.get("learning_status_summary", ""))
        payload["tomorrow_study_suggestions"] = [
            self._clean_markdown_text(item)
            for item in (payload.get("tomorrow_study_suggestions") or [])
            if self._clean_markdown_text(item)
        ]
        return payload

    def _load_latest_weekly_summary(self, workspace: Path) -> dict[str, Any]:
        path = self._latest_file(workspace / "memory" / "weekly_memory", ".md")
        if path is None or not path.exists():
            return {
                "title": "",
                "period": "",
                "goals": [],
                "daily_topics": [],
                "review_points": [],
                "correction_focus": [],
                "exercise_load": [],
                "difficulty_adjustment": [],
            }
        text = path.read_text(encoding="utf-8")
        lines = [line.rstrip() for line in text.splitlines()]
        title = lines[0].lstrip("# ").strip() if lines else ""
        sections = self._parse_markdown_sections(lines)
        return {
            "title": title,
            "period": path.parent.name.replace("_", "."),
            "goals": sections.get("1. 本周目标", []),
            "daily_topics": sections.get("2. 每天建议主题", []),
            "review_points": sections.get("3. 优先复习知识点", []),
            "correction_focus": sections.get("4. 重点纠错方向", []),
            "exercise_load": sections.get("5. 推荐练习量", []),
            "difficulty_adjustment": sections.get("6. 难度调整建议", []),
        }

    @staticmethod
    def _parse_markdown_sections(lines: list[str]) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for raw in lines:
            line = raw.strip()
            if line.startswith("## "):
                current = line[3:].strip()
                sections[current] = []
                continue
            if not current or not line:
                continue
            cleaned = ConsoleRuntime._clean_markdown_text(line.lstrip("*- ").strip())
            if cleaned:
                sections[current].append(cleaned)
        return sections

    @staticmethod
    def _clean_markdown_text(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"`([^`]*)`", r"\1", text)
        text = re.sub(r"\$(.*?)\$", r"\1", text)
        text = text.replace("__", "").replace("**", "").replace("•", "·")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _top_nodes(graph: dict[str, Any], kind: str) -> list[dict[str, Any]]:
        nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
        scored = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if kind == "error":
                score = float(node.get("severity", 0.0)) * 0.7 + min(float(node.get("error_count", 0)) / 5.0, 1.0) * 0.3
            else:
                score = float(node.get("risk", 0.0)) * 0.65 + float(node.get("importance", 0.0)) * 0.35
            scored.append((score, node))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "id": str(node.get("id", "")),
                "label": str(node.get("label", "")),
                "summary": str(node.get("notes") or node.get("summary") or ""),
                "score": round(score, 2),
            }
            for score, node in scored[:5]
        ]

    @staticmethod
    def _latest_file(base: Path, suffix: str) -> Path | None:
        if not base.exists():
            return None
        files = sorted(base.glob(f"*/*{suffix}"))
        return files[-1] if files else None

    @staticmethod
    def _read_json_file(path: Path | None) -> dict[str, Any]:
        if path is None or not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        items: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if isinstance(payload, dict):
                items.append(payload)
        return items

    @staticmethod
    def _ms_to_iso(value: Any) -> str | None:
        if not value:
            return None
        try:
            return datetime.fromtimestamp(int(value) / 1000).isoformat(timespec="minutes")
        except Exception:
            return None

    @staticmethod
    def _read_pid(path: Path) -> int | None:
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except Exception:
            return None

    @staticmethod
    def _read_cmdline(pid: int | None) -> list[str]:
        if not pid:
            return []
        path = Path(f"/proc/{pid}/cmdline")
        if not path.exists():
            return []
        try:
            return [part for part in path.read_text(encoding="utf-8").split("\0") if part]
        except Exception:
            return []

    @staticmethod
    def _pid_alive(pid: int | None) -> bool:
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _read_graph_file(path: Path, fallback_name: str) -> dict[str, Any]:
        if not path.exists():
            return {"graph": fallback_name, "updated_at": None, "nodes": [], "edges": []}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {"graph": fallback_name, "updated_at": None, "nodes": [], "edges": []}
        payload.setdefault("graph", fallback_name)
        payload.setdefault("updated_at", None)
        payload.setdefault("nodes", [])
        payload.setdefault("edges", [])
        return payload

    @classmethod
    def _content_to_payload(cls, content: Any) -> dict[str, Any]:
        if isinstance(content, str):
            return {
                "content": content,
                "attachments": [],
            }
        if isinstance(content, list):
            chunks: list[str] = []
            attachments: list[dict[str, str]] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type == "text":
                    text = block.get("text", "")
                    if text:
                        chunks.append(str(text))
                elif block_type in {"image_url", "input_image"}:
                    attachment = cls._extract_attachment(block, "image")
                    if attachment:
                        attachments.append(attachment)
                elif block_type in {"file", "input_file"}:
                    attachment = cls._extract_attachment(block, "file")
                    if attachment:
                        attachments.append(attachment)
            return {
                "content": "\n".join(chunk for chunk in chunks if chunk).strip(),
                "attachments": attachments,
            }
        return {"content": "", "attachments": []}

    @classmethod
    def _extract_attachment(cls, block: dict[str, Any], fallback_kind: str) -> dict[str, str] | None:
        raw = block.get("image_url") or block.get("file") or block.get("input_file") or block.get("input_image") or block.get("url") or {}
        url = ""
        if isinstance(raw, dict):
            url = str(raw.get("url") or raw.get("file_url") or raw.get("path") or "")
        elif raw:
            url = str(raw)
        if not url:
            return None
        return cls._attachment_from_url(url, fallback_kind)

    @staticmethod
    def _attachment_from_url(url: str, kind: str) -> dict[str, str]:
        name = Path(urlparse(url).path).name or ("图片" if kind == "image" else "附件")
        public_url = url
        if url.startswith("/") and Path(url).exists():
            public_url = f"/uploads/{Path(url).name}"
        return {
            "kind": kind,
            "name": name,
            "url": public_url,
        }

    @classmethod
    def _serialize_messages(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for index, message in enumerate(messages):
            role = message.get("role")
            if role not in {"user", "assistant"}:
                continue

            payload = cls._content_to_payload(message.get("content"))
            content = payload.get("content", "")
            attachments = payload.get("attachments", [])
            if not content.strip():
                if not attachments:
                    continue

            serialized.append(
                {
                    "id": f"{role}-{index}",
                    "role": role,
                    "content": content,
                    "attachments": attachments,
                    "timestamp": str(message.get("timestamp", "")),
                }
            )
        return serialized

    def history(self) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(self._history(), self.loop)
            return future.result(timeout=60)

    def send(self, content: str, media: list[str] | None = None) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(self._send(content, media), self.loop)
            return future.result(timeout=600)

    def graphs(self) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(self._graphs(), self.loop)
            return future.result(timeout=60)

    def dashboard(self) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(self._dashboard(), self.loop)
            return future.result(timeout=60)

    def delete_graph_node(self, graph: str, node_id: str) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._delete_graph_node(graph, node_id),
                self.loop,
            )
            return future.result(timeout=60)

    def list_custom_output_skills(self) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(self._list_custom_output_skills(), self.loop)
            return future.result(timeout=60)

    def create_custom_output_skill(self, requirement: str) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._create_custom_output_skill(requirement),
                self.loop,
            )
            return future.result(timeout=180)

    def toggle_custom_output_skill(self, skill_id: str, enabled: bool) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._toggle_custom_output_skill(skill_id, enabled),
                self.loop,
            )
            return future.result(timeout=60)

    def delete_custom_output_skill(self, skill_id: str) -> dict[str, Any]:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(
                self._delete_custom_output_skill(skill_id),
                self.loop,
            )
            return future.result(timeout=60)

    def reset(self) -> None:
        with self._request_lock:
            future = asyncio.run_coroutine_threadsafe(self._send("/new"), self.loop)
            future.result(timeout=60)

    def close(self) -> None:
        if not self.loop.is_running():
            return

        async def _shutdown() -> None:
            if self.agent is not None:
                await self.agent.close_mcp()

        future = asyncio.run_coroutine_threadsafe(_shutdown(), self.loop)
        future.result(timeout=30)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)


RUNTIME = ConsoleRuntime()


class ConsoleHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/uploads/"):
            self._handle_uploaded_asset(parsed.path.removeprefix("/uploads/"))
            return
        if parsed.path == "/api/chat/messages":
            self._handle_chat_history()
            return
        if parsed.path == "/api/dashboard":
            self._handle_dashboard()
            return
        if parsed.path == "/api/memory/graphs":
            self._handle_memory_graphs()
            return
        if parsed.path == "/api/custom-output-skills":
            self._handle_custom_output_skill_list()
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/chat/messages":
            self._handle_chat_send()
            return
        if parsed.path == "/api/chat/uploads":
            self._handle_chat_uploads()
            return
        if parsed.path == "/api/memory/graphs/delete":
            self._handle_memory_graph_delete()
            return
        if parsed.path == "/api/custom-output-skills":
            self._handle_custom_output_skill_create()
            return
        if parsed.path == "/api/custom-output-skills/toggle":
            self._handle_custom_output_skill_toggle()
            return
        if parsed.path == "/api/custom-output-skills/delete":
            self._handle_custom_output_skill_delete()
            return
        self._write_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _handle_chat_history(self) -> None:
        try:
            self._write_json(RUNTIME.history())
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_dashboard(self) -> None:
        try:
            self._write_json(RUNTIME.dashboard())
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_memory_graphs(self) -> None:
        try:
            self._write_json(RUNTIME.graphs())
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_memory_graph_delete(self) -> None:
        try:
            payload = self._read_json()
            graph = str(payload.get("graph", "")).strip()
            node_id = str(payload.get("node_id", "")).strip()
            if not graph or not node_id:
                self._write_json({"error": "缺少 graph 或 node_id。"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json(RUNTIME.delete_graph_node(graph, node_id))
        except ValueError as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except KeyError as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_custom_output_skill_list(self) -> None:
        try:
            self._write_json(RUNTIME.list_custom_output_skills())
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_custom_output_skill_create(self) -> None:
        try:
            payload = self._read_json()
            requirement = str(payload.get("requirement", "")).strip()
            if not requirement:
                self._write_json({"error": "请输入想要的输出风格说明。"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json(RUNTIME.create_custom_output_skill(requirement))
        except ValueError as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_custom_output_skill_toggle(self) -> None:
        try:
            payload = self._read_json()
            skill_id = str(payload.get("id", "")).strip()
            if not skill_id:
                self._write_json({"error": "缺少 skill id。"}, status=HTTPStatus.BAD_REQUEST)
                return
            enabled = bool(payload.get("enabled", False))
            self._write_json(RUNTIME.toggle_custom_output_skill(skill_id, enabled))
        except KeyError as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_custom_output_skill_delete(self) -> None:
        try:
            payload = self._read_json()
            skill_id = str(payload.get("id", "")).strip()
            if not skill_id:
                self._write_json({"error": "缺少 skill id。"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json(RUNTIME.delete_custom_output_skill(skill_id))
        except KeyError as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.NOT_FOUND)
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_chat_send(self) -> None:
        try:
            payload = self._read_json()
            content = str(payload.get("content", "")).strip()
            media = payload.get("media", [])
            if not isinstance(media, list):
                media = []
            media = [str(item) for item in media if item]
            if not content and not media:
                self._write_json({"error": "消息不能为空"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json(RUNTIME.send(content, media))
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_chat_uploads(self) -> None:
        try:
            files = self._read_uploaded_files()
            if not files:
                self._write_json({"error": "没有收到文件"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json({"files": files})
        except Exception as error:
            self._write_json({"error": str(error)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_uploaded_asset(self, filename: str) -> None:
        target = UPLOAD_DIR / os.path.basename(filename)
        if not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self.path = f"/{target.name}"
        self.directory = str(UPLOAD_DIR)
        return super().do_GET()

    def _read_uploaded_files(self) -> list[dict[str, Any]]:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )

        items = form["files"] if "files" in form else []
        if not isinstance(items, list):
            items = [items]

        uploaded: list[dict[str, Any]] = []
        for item in items:
            if not getattr(item, "filename", ""):
                continue
            filename = os.path.basename(str(item.filename))
            suffix = Path(filename).suffix
            target = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
            data = item.file.read()
            target.write_bytes(data)
            uploaded.append(
                {
                    "name": filename,
                    "path": str(target),
                    "url": f"/uploads/{target.name}",
                    "size": len(data),
                }
            )
        if uploaded:
            with UPLOAD_LOG.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "session_key": SESSION_KEY,
                            "timestamp": datetime.now().isoformat(timespec="seconds"),
                            "count": 1,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return uploaded


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), ConsoleHandler)
    print(f"Serving nanobot console at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        RUNTIME.close()
