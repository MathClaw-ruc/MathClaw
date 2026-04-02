"""Structured learning memory for daily summaries, weekly plans, and graph snapshots."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import weakref
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger

from nanobot.utils.helpers import ensure_dir, estimate_message_tokens, estimate_prompt_tokens_chain

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider, LLMResponse
    from nanobot.session.manager import Session, SessionManager


_SAVE_LEARNING_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_learning_memory",
            "description": (
                "Store the day's learning memory in a structured format for daily summaries "
                "and two graph snapshots: knowledge points and mistake patterns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "learning_status_summary": {"type": "string"},
                    "tomorrow_study_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "high_risk_knowledge_points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "risk": {"type": "number"},
                                "mastery": {"type": "number"},
                                "importance": {"type": "number"},
                                "notes": {"type": "string"},
                                "examples": {"type": "array", "items": {"type": "string"}},
                                "prerequisites": {"type": "array", "items": {"type": "string"}},
                                "similar_points": {"type": "array", "items": {"type": "string"}},
                                "contains_points": {"type": "array", "items": {"type": "string"}},
                                "related_points": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["label"],
                        },
                    },
                    "high_frequency_error_types": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "severity": {"type": "number"},
                                "repeated": {"type": "boolean"},
                                "notes": {"type": "string"},
                                "classic_example": {"type": "string"},
                                "examples": {"type": "array", "items": {"type": "string"}},
                                "related_knowledge_points": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "similar_errors": {"type": "array", "items": {"type": "string"}},
                                "correction_suggestions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["label"],
                        },
                    },
                },
                "required": [
                    "date",
                    "high_risk_knowledge_points",
                    "high_frequency_error_types",
                    "learning_status_summary",
                    "tomorrow_study_suggestions",
                ],
            },
        },
    }
]

_TOOL_CHOICE_ERROR_MARKERS = (
    "tool_choice",
    "toolchoice",
    "does not support",
    'should be ["none", "auto"]',
)

_LOW_SIGNAL_DAYS = 45
_CANDIDATE_STALE_DAYS = 12
_GRAPH_EXAMPLE_RETENTION_DAYS = 15
_MAX_GRAPH_EXAMPLES = 8
_MAX_GRAPH_CONTEXT_ITEMS = 6
_MAX_WEEKLY_DAYS = 7
_MAX_MEMORY_CONTEXT_CHARS = 1200
_ACTIVE_NODE_LIMITS = {"knowledge": 18, "error": 14}
_CANDIDATE_NODE_LIMITS = {"knowledge": 12, "error": 10}


def _is_tool_choice_unsupported(content: str | None) -> bool:
    text = (content or "").lower()
    return any(marker in text for marker in _TOOL_CHOICE_ERROR_MARKERS)


def _normalize_tool_args(args: Any) -> dict[str, Any] | None:
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return None
    if isinstance(args, list):
        return args[0] if args and isinstance(args[0], dict) else None
    return args if isinstance(args, dict) else None


def _extract_json_object(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("Z"):
            stripped = stripped[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(stripped)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(stripped, fmt)
            except ValueError:
                continue
    return datetime.now()


def _day_dir_name(day: date) -> str:
    return f"{day.year}.{day.month}.{day.day}"


def _day_file_stem(day: date) -> str:
    return f"{day.year}_{day.month}_{day.day}"


def _week_file_stem(end_day: date) -> str:
    start_day = end_day - timedelta(days=_MAX_WEEKLY_DAYS - 1)
    return (
        f"{start_day.year}_{start_day.month}_{start_day.day}_to_"
        f"{end_day.year}_{end_day.month}_{end_day.day}"
    )


def _clamp(value: Any, default: float, *, low: float = 0.0, high: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(low, min(high, numeric))


def _blend(previous: Any, incoming: Any, *, default: float) -> float:
    before = _clamp(previous, default)
    after = _clamp(incoming, before)
    return round((before + after) / 2, 4)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _dedupe_texts(values: list[str], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = value.strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def _coerce_text_list(value: Any, *, limit: int | None = None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return _dedupe_texts(re.split(r"[\n;,，；]+", value), limit=limit)
    if isinstance(value, list):
        return _dedupe_texts([_as_text(item) for item in value], limit=limit)
    return _dedupe_texts([_as_text(value)], limit=limit)


def _join_notes(*values: Any) -> str:
    parts = _dedupe_texts([_as_text(value) for value in values if _as_text(value).strip()], limit=3)
    return "；".join(parts)


def _prefer_text(*values: Any) -> str:
    candidates = [_as_text(value).strip() for value in values if _as_text(value).strip()]
    if not candidates:
        return ""
    return max(
        candidates,
        key=lambda text: (
            len(text),
            sum(char in "，。；：、（）()" for char in text),
        ),
    )


def _safe_node_id(prefix: str, label: str) -> str:
    normalized = re.sub(r"\s+", "-", label.strip().casefold())
    slug = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "-", normalized).strip("-")
    digest = hashlib.sha1(label.strip().encode("utf-8")).hexdigest()[:10]
    if slug:
        return f"{prefix}:{slug[:24]}-{digest}"
    return f"{prefix}:item-{digest}"


def _query_terms(text: str, *, limit: int = 12) -> list[str]:
    if not text:
        return []
    seen: set[str] = set()
    terms: list[str] = []
    for match in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_+\-]{2,}", text):
        token = match.strip().casefold()
        if not token or token in seen:
            continue
        seen.add(token)
        terms.append(match.strip())
        if len(terms) >= limit:
            break
    return terms


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load JSON from {}", path)
        return default


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class MemoryStore:
    """Daily/weekly learning memory plus two lightweight graph snapshots."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory")
        self.daily_memory_dir = ensure_dir(self.memory_dir / "daily_memory")
        self.weekly_memory_dir = ensure_dir(self.memory_dir / "weekly_memory")
        self.daily_conversations_dir = ensure_dir(self.memory_dir / "daily_conversations")
        self.graph_dir = ensure_dir(self.memory_dir / "graphs")

        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"
        self.knowledge_graph_file = self.graph_dir / "knowledge_graph.json"
        self.error_graph_file = self.graph_dir / "error_graph.json"

        if not self.history_file.exists():
            self.history_file.write_text("", encoding="utf-8")
        self._ensure_graph_file(self.knowledge_graph_file, "knowledge")
        self._ensure_graph_file(self.error_graph_file, "error")

    def _ensure_graph_file(self, path: Path, graph_name: str) -> None:
        if path.exists():
            return
        _save_json(path, {
            "graph": graph_name,
            "updated_at": None,
            "nodes": [],
            "edges": [],
            "archived_nodes": [],
        })

    def read_long_term(self) -> str:
        return self.memory_file.read_text(encoding="utf-8") if self.memory_file.exists() else ""

    def write_long_term(self, content: str) -> None:
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        with open(self.history_file, "a", encoding="utf-8") as handle:
            handle.write(entry.rstrip() + "\n")

    def get_memory_context(self) -> str:
        snapshot = self._build_memory_snapshot()
        if not snapshot:
            return ""
        self.write_long_term(snapshot)
        return snapshot

    @staticmethod
    def _format_messages(messages: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for message in messages:
            content = _as_text(message.get("content")).strip()
            if not content:
                continue
            timestamp = _parse_timestamp(message.get("timestamp")).strftime("%Y-%m-%d %H:%M")
            role = str(message.get("role", "unknown")).upper()
            session_key = str(message.get("session_key", "")).strip()
            prefix = f"[{timestamp}]"
            if session_key:
                prefix += f" [{session_key}]"
            lines.append(f"{prefix} {role}: {content}")
        return "\n".join(lines)

    async def consolidate(
        self,
        messages: list[dict[str, Any]],
        provider: LLMProvider,
        model: str,
        *,
        session_key: str | None = None,
    ) -> bool:
        """Persist archived messages into day buckets, summaries, and graph snapshots."""
        if not messages:
            return True

        grouped = self._group_messages_by_day(messages, session_key=session_key)
        if not grouped:
            return True

        touched_days: set[date] = set()
        for day, day_messages in grouped.items():
            self._append_day_events(day, day_messages)
            touched_days.add(day)
            self.append_history(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] "
                f"archived {len(day_messages)} messages -> {day.isoformat()}"
                + (f" ({session_key})" if session_key else "")
            )

        for day in sorted(touched_days):
            try:
                await self._refresh_daily_summary(day, provider, model)
            except Exception:
                logger.exception("Failed to refresh daily memory for {}", day.isoformat())

        for day in sorted(touched_days):
            try:
                await self._refresh_weekly_plan(day, provider, model)
            except Exception:
                logger.exception("Failed to refresh weekly memory ending on {}", day.isoformat())

        self.get_memory_context()
        return True

    def _group_messages_by_day(
        self,
        messages: list[dict[str, Any]],
        *,
        session_key: str | None,
    ) -> dict[date, list[dict[str, Any]]]:
        grouped: dict[date, list[dict[str, Any]]] = {}
        for message in messages:
            if message.get("summary_push"):
                continue
            observed_at = _parse_timestamp(message.get("timestamp"))
            enriched = {
                "session_key": session_key or message.get("session_key", ""),
                "timestamp": observed_at.isoformat(),
                "role": message.get("role", "unknown"),
                "content": _as_text(message.get("content")),
            }
            if message.get("tools_used"):
                enriched["tools_used"] = message.get("tools_used")
            grouped.setdefault(observed_at.date(), []).append(enriched)
        return grouped

    def _day_paths(self, day: date) -> tuple[Path, Path, Path, Path]:
        day_root = ensure_dir(self.daily_memory_dir / _day_dir_name(day))
        conversation_root = ensure_dir(self.daily_conversations_dir / _day_dir_name(day))
        stem = _day_file_stem(day)
        return (
            day_root,
            day_root / f"{stem}.md",
            day_root / f"{stem}.json",
            conversation_root / "events.jsonl",
        )

    def _append_day_events(self, day: date, messages: list[dict[str, Any]]) -> None:
        merged = self._dedupe_events([*self._load_day_events(day), *messages])
        self._write_day_events(day, merged)

    def _load_day_events(self, day: date) -> list[dict[str, Any]]:
        _, _, _, events_file = self._day_paths(day)
        legacy_events_file = self.daily_memory_dir / _day_dir_name(day) / "events.jsonl"
        events: list[dict[str, Any]] = []
        for path in (events_file, legacy_events_file):
            if not path.exists():
                continue
            events.extend(self._load_events_file(path))
        return self._dedupe_events(events)

    def _load_events_file(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []

        payloads: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                payloads.append(payload)
        return payloads

    @staticmethod
    def _event_fingerprint(payload: dict[str, Any]) -> str:
        return json.dumps(
            {
                "session_key": payload.get("session_key"),
                "timestamp": payload.get("timestamp"),
                "role": payload.get("role"),
                "content": payload.get("content"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def _dedupe_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: dict[str, dict[str, Any]] = {}
        for payload in events:
            if not isinstance(payload, dict):
                continue
            unique[self._event_fingerprint(payload)] = payload
        return sorted(unique.values(), key=lambda item: item.get("timestamp", ""))

    def _write_day_events(self, day: date, events: list[dict[str, Any]]) -> None:
        _, _, _, events_file = self._day_paths(day)
        legacy_events_file = self.daily_memory_dir / _day_dir_name(day) / "events.jsonl"
        events_file.parent.mkdir(parents=True, exist_ok=True)
        with open(events_file, "w", encoding="utf-8") as handle:
            for payload in self._dedupe_events(events):
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        if legacy_events_file.exists() and legacy_events_file != events_file:
            legacy_events_file.unlink()

    def collect_day_events(
        self,
        day: date,
        sessions: "SessionManager",
    ) -> list[dict[str, Any]]:
        combined = list(self._load_day_events(day))
        for item in sessions.list_sessions():
            session_key = str(item.get("key") or "").strip()
            if not session_key:
                continue
            session = sessions.get_or_create(session_key)
            for message in session.messages:
                if message.get("summary_push"):
                    continue
                role = str(message.get("role", "")).strip()
                if role not in {"user", "assistant"}:
                    continue
                observed_at = _parse_timestamp(message.get("timestamp"))
                if observed_at.date() != day:
                    continue
                combined.append(
                    {
                        "session_key": session_key,
                        "timestamp": observed_at.isoformat(),
                        "role": role,
                        "content": _as_text(message.get("content")),
                    }
                )
        merged = self._dedupe_events(combined)
        self._write_day_events(day, merged)
        return merged

    async def _refresh_daily_summary(self, day: date, provider: LLMProvider, model: str) -> None:
        await self.ensure_daily_summary(day, provider, model)

    async def ensure_daily_summary(
        self,
        day: date,
        provider: LLMProvider,
        model: str,
        *,
        sessions: "SessionManager | None" = None,
    ) -> str | None:
        events = self.collect_day_events(day, sessions) if sessions else self._load_day_events(day)
        if not events:
            return None

        payload = await self._summarize_day(day, events, provider, model)
        self._write_daily_files(day, payload, events)
        self._update_knowledge_graph(day, payload["high_risk_knowledge_points"])
        self._update_error_graph(day, payload["high_frequency_error_types"])
        _, markdown_file, _, _ = self._day_paths(day)
        return markdown_file.read_text(encoding="utf-8")

    async def _summarize_day(
        self,
        day: date,
        events: list[dict[str, Any]],
        provider: LLMProvider,
        model: str,
    ) -> dict[str, Any]:
        prompt = f"""Analyze the archived learning conversations for {day.isoformat()}.

Return a structured learning-memory result through the save_learning_memory tool.

Requirements:
- Focus on math learning state, weak knowledge points, and repeated error patterns.
- Deduplicate overlapping concepts.
- Use 0..1 floats for risk/mastery/importance/severity.
- Keep high_risk_knowledge_points and high_frequency_error_types concise (prefer <= 8 items each).
- Use simple Chinese phrases if possible.
- Error-pattern labels must be generic reusable pattern titles, not one-off题面碎片或变量片段。
- For each error pattern, provide one short classic_example.

Conversation Archive:
{self._format_messages(events)}
"""

        chat_messages = [
            {
                "role": "system",
                "content": (
                    "You are a memory consolidation agent for a math learning assistant. "
                    "Always call save_learning_memory with a concise structured payload."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        raw_payload: dict[str, Any] | None = None
        try:
            forced = {"type": "function", "function": {"name": "save_learning_memory"}}
            response: LLMResponse = await provider.chat_with_retry(
                messages=chat_messages,
                tools=_SAVE_LEARNING_MEMORY_TOOL,
                model=model,
                tool_choice=forced,
            )
            if response.finish_reason == "error" and _is_tool_choice_unsupported(response.content):
                response = await provider.chat_with_retry(
                    messages=chat_messages,
                    tools=_SAVE_LEARNING_MEMORY_TOOL,
                    model=model,
                    tool_choice="auto",
                )
            if response.has_tool_calls:
                raw_payload = _normalize_tool_args(response.tool_calls[0].arguments)
            if raw_payload is None:
                raw_payload = _extract_json_object(response.content)
        except Exception:
            logger.exception("Daily learning memory summarization failed for {}", day.isoformat())

        payload = self._normalize_daily_payload(day, raw_payload)
        if payload:
            return payload
        return self._fallback_daily_payload(day, events)

    def _normalize_daily_payload(self, day: date, payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None

        summary = _as_text(
            payload.get("learning_status_summary")
            or payload.get("study_status_summary")
            or payload.get("summary")
        ).strip()
        suggestions = _coerce_text_list(
            payload.get("tomorrow_study_suggestions")
            or payload.get("tomorrow_suggestions")
            or payload.get("next_steps"),
            limit=6,
        )
        if not summary and not suggestions:
            return None

        knowledge_points: list[dict[str, Any]] = []
        for raw in payload.get("high_risk_knowledge_points") or []:
            item = self._normalize_knowledge_point(day, raw)
            if item:
                knowledge_points.append(item)

        error_types: list[dict[str, Any]] = []
        for raw in payload.get("high_frequency_error_types") or []:
            item = self._normalize_error_type(day, raw)
            if item:
                error_types.append(item)

        return {
            "date": _as_text(payload.get("date")).strip() or day.isoformat(),
            "high_risk_knowledge_points": knowledge_points,
            "high_frequency_error_types": error_types,
            "learning_status_summary": summary,
            "tomorrow_study_suggestions": suggestions,
        }

    def _normalize_knowledge_point(self, day: date, raw: Any) -> dict[str, Any] | None:
        if isinstance(raw, str):
            label = raw.strip()
            if not label:
                return None
            return {
                "label": label,
                "risk": 0.6,
                "mastery": 0.4,
                "importance": 0.6,
                "notes": "",
                "last_seen": day.isoformat(),
                "examples": [],
                "prerequisites": [],
                "similar_points": [],
                "contains_points": [],
                "related_points": [],
            }
        if not isinstance(raw, dict):
            return None
        label = _as_text(raw.get("label") or raw.get("name") or raw.get("point")).strip()
        if not label:
            return None
        return {
            "label": label,
            "risk": _clamp(raw.get("risk") or raw.get("risk_score"), 0.6),
            "mastery": _clamp(raw.get("mastery") or raw.get("mastery_score"), 0.4),
            "importance": _clamp(raw.get("importance") or raw.get("weight"), 0.6),
            "notes": _as_text(raw.get("notes") or raw.get("reason")).strip(),
            "last_seen": day.isoformat(),
            "examples": _coerce_text_list(raw.get("examples"), limit=4),
            "prerequisites": _coerce_text_list(raw.get("prerequisites"), limit=6),
            "similar_points": _coerce_text_list(raw.get("similar_points"), limit=6),
            "contains_points": _coerce_text_list(raw.get("contains_points"), limit=6),
            "related_points": _coerce_text_list(raw.get("related_points"), limit=8),
        }

    def _normalize_error_type(self, day: date, raw: Any) -> dict[str, Any] | None:
        if isinstance(raw, str):
            label = raw.strip()
            if not label:
                return None
            return {
                "label": label,
                "severity": 0.6,
                "repeated": False,
                "notes": "",
                "last_seen": day.isoformat(),
                "classic_example": "",
                "examples": [],
                "related_knowledge_points": [],
                "similar_errors": [],
                "correction_suggestions": [],
            }
        if not isinstance(raw, dict):
            return None
        label = _as_text(raw.get("label") or raw.get("name") or raw.get("pattern")).strip()
        if not label:
            return None
        return {
            "label": label,
            "severity": _clamp(raw.get("severity") or raw.get("risk"), 0.6),
            "repeated": bool(raw.get("repeated") or raw.get("repeat")),
            "notes": _as_text(raw.get("notes") or raw.get("reason")).strip(),
            "last_seen": day.isoformat(),
            "classic_example": _as_text(raw.get("classic_example") or raw.get("representative_example")).strip(),
            "examples": _coerce_text_list(raw.get("examples"), limit=4),
            "related_knowledge_points": _coerce_text_list(raw.get("related_knowledge_points"), limit=6),
            "similar_errors": _coerce_text_list(raw.get("similar_errors"), limit=6),
            "correction_suggestions": _coerce_text_list(raw.get("correction_suggestions"), limit=6),
        }

    def _fallback_daily_payload(self, day: date, events: list[dict[str, Any]]) -> dict[str, Any]:
        session_count = len({item.get("session_key") for item in events if item.get("session_key")})
        user_messages = sum(1 for item in events if item.get("role") == "user")
        assistant_messages = sum(1 for item in events if item.get("role") == "assistant")
        return {
            "date": day.isoformat(),
            "high_risk_knowledge_points": [],
            "high_frequency_error_types": [],
            "learning_status_summary": (
                f"当天共归档 {len(events)} 条消息，涉及 {session_count or 1} 个会话，"
                f"其中用户消息 {user_messages} 条、助手消息 {assistant_messages} 条。"
            ),
            "tomorrow_study_suggestions": [
                "优先复盘当天未完全掌握的题目。",
                "整理重复出错的步骤，作为明天开场复习清单。",
            ],
        }

    def _write_daily_files(
        self,
        day: date,
        payload: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> None:
        _, markdown_file, json_file, _ = self._day_paths(day)
        _save_json(json_file, payload)

        session_counter = Counter(str(item.get("session_key") or "unknown") for item in events)
        session_lines = [f"- `{name}`: {count} 条" for name, count in session_counter.most_common(6)]
        knowledge_lines = [
            f"- {item['label']} | 风险 {item['risk']:.2f} | 掌握度 {item['mastery']:.2f} | 重要度 {item['importance']:.2f}"
            + (f" | {item['notes']}" if item.get("notes") else "")
            for item in payload["high_risk_knowledge_points"]
        ] or ["- 暂无高风险知识点提炼。"]
        error_lines = [
            f"- {item['label']} | 严重度 {item['severity']:.2f}"
            + (" | 重复出现" if item.get("repeated") else "")
            + (f" | {item['notes']}" if item.get("notes") else "")
            for item in payload["high_frequency_error_types"]
        ] or ["- 暂无高频错误模式提炼。"]
        suggestion_lines = [f"- {item}" for item in payload["tomorrow_study_suggestions"]] or ["- 明天继续保持稳定复盘。"]

        markdown = "\n".join([
            f"# 每日学习记忆 - {payload['date']}",
            "",
            "## 学习状态总结",
            payload["learning_status_summary"],
            "",
            "## 高风险知识点",
            *knowledge_lines,
            "",
            "## 高频错误类型",
            *error_lines,
            "",
            "## 明天学习建议",
            *suggestion_lines,
            "",
            "## 当天会话分布",
            *(session_lines or ["- 暂无会话统计。"]),
        ])
        markdown_file.write_text(markdown, encoding="utf-8")

    def _load_graph(self, path: Path, fallback_name: str) -> dict[str, Any]:
        payload = _load_json(path, {})
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("graph", fallback_name)
        payload.setdefault("updated_at", None)
        payload.setdefault("nodes", [])
        payload.setdefault("edges", [])
        payload.setdefault("archived_nodes", [])
        payload = self._upgrade_graph_ids(payload, fallback_name)
        return payload

    def _upgrade_graph_ids(self, payload: dict[str, Any], graph_name: str) -> dict[str, Any]:
        prefix = "kp" if graph_name == "knowledge" else "err"
        id_map: dict[str, str] = {}

        def _rewrite_nodes(items: list[Any]) -> list[dict[str, Any]]:
            upgraded: dict[str, dict[str, Any]] = {}
            for raw in items:
                if not isinstance(raw, dict):
                    continue
                label = _as_text(raw.get("label")).strip()
                if not label:
                    continue
                new_id = _safe_node_id(prefix, label)
                old_id = _as_text(raw.get("id")).strip() or new_id
                id_map[old_id] = new_id
                candidate = {**raw, "id": new_id}
                existing = upgraded.get(new_id)
                if existing is None:
                    upgraded[new_id] = candidate
                    continue
                upgraded[new_id] = {
                    **existing,
                    **candidate,
                    "time_points": _dedupe_texts(
                        [*existing.get("time_points", []), *candidate.get("time_points", [])],
                        limit=12,
                    ),
                    "examples": self._merge_examples(
                        existing.get("examples", []),
                        candidate.get("examples", []),
                        datetime.now().date(),
                    ),
                }
            return list(upgraded.values())

        payload["nodes"] = _rewrite_nodes(payload.get("nodes", []))
        payload["archived_nodes"] = _rewrite_nodes(payload.get("archived_nodes", []))

        rewritten_edges: dict[tuple[str, str, str], dict[str, Any]] = {}
        for raw in payload.get("edges", []):
            if not isinstance(raw, dict):
                continue
            source = id_map.get(_as_text(raw.get("source")).strip(), _as_text(raw.get("source")).strip())
            target = id_map.get(_as_text(raw.get("target")).strip(), _as_text(raw.get("target")).strip())
            relation = _as_text(raw.get("relation")).strip()
            if not source or not target or not relation:
                continue
            rewritten_edges[(source, target, relation)] = {**raw, "source": source, "target": target}
        payload["edges"] = list(rewritten_edges.values())
        return payload

    def _save_graph(self, path: Path, payload: dict[str, Any]) -> None:
        payload["updated_at"] = datetime.now().isoformat()
        _save_json(path, payload)

    def delete_graph_node(self, kind: str, node_id: str) -> None:
        kind = kind.strip().lower()
        if kind not in {"knowledge", "error"}:
            raise ValueError(f"Unsupported graph kind: {kind}")
        node_id = _as_text(node_id).strip()
        if not node_id:
            raise ValueError("Missing graph node id.")

        path = self.knowledge_graph_file if kind == "knowledge" else self.error_graph_file
        graph = self._load_graph(path, kind)
        today = datetime.now().date()

        visible_nodes = [
            dict(item)
            for item in graph.get("nodes", [])
            if isinstance(item, dict) and item.get("id")
        ]
        archived_nodes = [
            dict(item)
            for item in graph.get("archived_nodes", [])
            if isinstance(item, dict) and item.get("id")
        ]
        removed = any(item.get("id") == node_id for item in visible_nodes) or any(
            item.get("id") == node_id for item in archived_nodes
        )
        if not removed:
            raise KeyError(f"Graph node not found: {node_id}")

        graph["nodes"] = [item for item in visible_nodes if item.get("id") != node_id]
        graph["archived_nodes"] = [item for item in archived_nodes if item.get("id") != node_id]
        graph["edges"] = [
            dict(edge)
            for edge in graph.get("edges", [])
            if isinstance(edge, dict)
            and edge.get("source") != node_id
            and edge.get("target") != node_id
        ]

        graph["nodes"], graph["archived_nodes"], graph["focus_node_ids"] = self._rebalance_graph_nodes(
            kind,
            graph["nodes"],
            graph["archived_nodes"],
            today,
        )
        visible_ids = {item["id"] for item in graph["nodes"]}
        active_ids = {item["id"] for item in graph["nodes"] if item.get("status") == "active"}
        if kind == "knowledge":
            graph["edges"] = [
                {
                    **edge,
                    "status": (
                        "active"
                        if edge.get("source") in active_ids and edge.get("target") in active_ids
                        else "candidate"
                    ),
                }
                for edge in graph["edges"]
                if edge.get("source") in visible_ids
                and edge.get("target") in visible_ids
                and edge.get("source") != edge.get("target")
            ]
        else:
            graph["edges"] = [
                {
                    **edge,
                    "status": (
                        "active"
                        if edge.get("source") in active_ids and (
                            _as_text(edge.get("target")).startswith("kp:") or edge.get("target") in active_ids
                        )
                        else "candidate"
                    ),
                }
                for edge in graph["edges"]
                if edge.get("source") in visible_ids
                and (
                    _as_text(edge.get("target")).startswith("kp:") or edge.get("target") in visible_ids
                )
                and edge.get("source") != edge.get("target")
            ]

        graph["stats"] = {
            "active": len(active_ids),
            "candidate": sum(1 for item in graph["nodes"] if item.get("status") == "candidate"),
            "archived": len(graph["archived_nodes"]),
        }
        self._save_graph(path, graph)

    @staticmethod
    def _graph_score(kind: str, node: dict[str, Any], today: date) -> float:
        last_seen = _parse_timestamp(node.get("last_seen")).date()
        freshness = max(0, 14 - (today - last_seen).days)
        if kind == "knowledge":
            return round(
                _clamp(node.get("importance"), 0.0) * 2.8
                + _clamp(node.get("risk"), 0.0) * 2.0
                + int(node.get("occurrences", 0)) * 0.45
                + freshness * 0.08,
                4,
            )
        return round(
            _clamp(node.get("severity"), 0.0) * 2.6
            + int(node.get("error_count", 0)) * 0.7
            + (0.8 if node.get("repeated") else 0.0)
            + freshness * 0.08,
            4,
        )

    @staticmethod
    def _candidate_drop(kind: str, node: dict[str, Any], today: date) -> bool:
        last_seen = _parse_timestamp(node.get("last_seen")).date()
        age = (today - last_seen).days
        if age < _CANDIDATE_STALE_DAYS:
            return False
        if kind == "knowledge":
            return (
                int(node.get("occurrences", 0)) <= 1
                and _clamp(node.get("importance"), 0.0) < 0.68
                and _clamp(node.get("risk"), 0.0) < 0.68
            )
        return (
            int(node.get("error_count", 0)) <= 1
            and _clamp(node.get("severity"), 0.0) < 0.68
            and not node.get("repeated")
        )

    @staticmethod
    def _target_node_status(kind: str, node: dict[str, Any], today: date) -> str:
        last_seen = _parse_timestamp(node.get("last_seen")).date()
        age = (today - last_seen).days

        if kind == "knowledge":
            if age >= _LOW_SIGNAL_DAYS and (
                _clamp(node.get("importance"), 0.0) < 0.35
                and _clamp(node.get("risk"), 0.0) < 0.35
            ):
                return "archived"
            if (
                int(node.get("occurrences", 0)) >= 2
                or len(node.get("time_points", []) or []) >= 2
                or _clamp(node.get("importance"), 0.0) >= 0.72
                or _clamp(node.get("risk"), 0.0) >= 0.7
            ):
                return "active"
        else:
            if age >= _LOW_SIGNAL_DAYS and (
                _clamp(node.get("severity"), 0.0) < 0.35
                and int(node.get("error_count", 0)) <= 1
            ):
                return "archived"
            if (
                int(node.get("error_count", 0)) >= 2
                or node.get("repeated")
                or _clamp(node.get("severity"), 0.0) >= 0.68
            ):
                return "active"

        if MemoryStore._candidate_drop(kind, node, today):
            return "archived"
        return "candidate"

    def _rebalance_graph_nodes(
        self,
        kind: str,
        nodes: list[dict[str, Any]],
        archived_nodes: list[dict[str, Any]],
        today: date,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        archived_map = {
            item["id"]: dict(item)
            for item in archived_nodes
            if isinstance(item, dict) and item.get("id")
        }

        staged: list[dict[str, Any]] = []
        for raw in nodes:
            if not isinstance(raw, dict) or not raw.get("id"):
                continue
            node = dict(raw)
            target_status = self._target_node_status(kind, node, today)
            if target_status == "archived":
                node["status"] = "archived"
                archived_map[node["id"]] = node
                continue
            node["status"] = target_status
            staged.append(node)

        active_limit = _ACTIVE_NODE_LIMITS[kind]
        candidate_limit = _CANDIDATE_NODE_LIMITS[kind]
        active = sorted(
            [item for item in staged if item.get("status") == "active"],
            key=lambda item: (self._graph_score(kind, item, today), item.get("last_seen", "")),
            reverse=True,
        )
        candidate = sorted(
            [item for item in staged if item.get("status") == "candidate"],
            key=lambda item: (self._graph_score(kind, item, today), item.get("last_seen", "")),
            reverse=True,
        )

        if len(active) > active_limit:
            overflow = active[active_limit:]
            for item in overflow:
                item["status"] = "candidate"
            candidate = sorted(
                [*candidate, *overflow],
                key=lambda item: (self._graph_score(kind, item, today), item.get("last_seen", "")),
                reverse=True,
            )
            active = active[:active_limit]

        if len(candidate) > candidate_limit:
            for item in candidate[candidate_limit:]:
                item["status"] = "archived"
                archived_map[item["id"]] = item
            candidate = candidate[:candidate_limit]

        visible = [*active, *candidate]
        focus_ids = [item["id"] for item in active[:8]]
        if len(focus_ids) < 8:
            focus_ids.extend(item["id"] for item in candidate[: 8 - len(focus_ids)])

        archived = sorted(
            archived_map.values(),
            key=lambda item: item.get("last_seen", ""),
            reverse=True,
        )[:120]
        return visible, archived, focus_ids

    @staticmethod
    def _touch_edge(
        edges: dict[tuple[str, str, str], dict[str, Any]],
        key: tuple[str, str, str],
        day: date,
    ) -> None:
        source, target, relation = key
        current = edges.get(key, {
            "source": source,
            "target": target,
            "relation": relation,
            "occurrences": 0,
            "strength": 0.35,
        })
        already_seen_today = _as_text(current.get("updated_at")).strip() == day.isoformat()
        current["occurrences"] = int(current.get("occurrences", 0)) + (0 if already_seen_today else 1)
        current["updated_at"] = day.isoformat()
        current["strength"] = round(min(1.0, 0.3 + current["occurrences"] * 0.18), 2)
        edges[key] = current

    def apply_turn_graph_updates(
        self,
        day: date,
        *,
        knowledge_updates: list[dict[str, Any]] | None = None,
        error_updates: list[dict[str, Any]] | None = None,
    ) -> None:
        knowledge_items = [
            item
            for item in (
                self._normalize_knowledge_point(day, raw)
                for raw in (knowledge_updates or [])
            )
            if item
        ]
        error_items = [
            item
            for item in (
                self._normalize_error_type(day, raw)
                for raw in (error_updates or [])
            )
            if item
        ]
        if knowledge_items:
            self._update_knowledge_graph(day, knowledge_items)
        if error_items:
            self._update_error_graph(day, error_items)
        if knowledge_items or error_items:
            self.get_memory_context()

    def _update_knowledge_graph(self, day: date, items: list[dict[str, Any]]) -> None:
        graph = self._load_graph(self.knowledge_graph_file, "knowledge")
        nodes = {
            item["id"]: dict(item)
            for item in graph["nodes"]
            if isinstance(item, dict) and item.get("id")
        }
        archived = {
            item["id"]: dict(item)
            for item in graph.get("archived_nodes", [])
            if isinstance(item, dict) and item.get("id")
        }
        edges = {
            (edge["source"], edge["target"], edge["relation"]): dict(edge)
            for edge in graph["edges"]
            if isinstance(edge, dict)
            and edge.get("source")
            and edge.get("target")
            and edge.get("relation")
        }

        for item in items:
            node_id = _safe_node_id("kp", item["label"])
            current = nodes.get(node_id) or archived.pop(node_id, None) or {
                "id": node_id,
                "type": "knowledge_point",
                "label": item["label"],
                "occurrences": 0,
                "time_points": [],
                "examples": [],
                "status": "candidate",
            }
            already_seen_today = day.isoformat() in current.get("time_points", [])
            current["label"] = item["label"]
            current["risk"] = max(_clamp(current.get("risk"), 0.0), item["risk"])
            current["mastery"] = (
                item["mastery"]
                if already_seen_today
                else _blend(current.get("mastery"), item["mastery"], default=item["mastery"])
            )
            current["importance"] = max(_clamp(current.get("importance"), 0.0), item["importance"])
            current["occurrences"] = int(current.get("occurrences", 0)) + (0 if already_seen_today else 1)
            current["first_seen"] = current.get("first_seen") or day.isoformat()
            current["last_seen"] = day.isoformat()
            current["status"] = current.get("status", "candidate")
            current["notes"] = _join_notes(current.get("notes"), item.get("notes"))
            current["time_points"] = _dedupe_texts([*current.get("time_points", []), day.isoformat()], limit=12)
            current["examples"] = self._merge_examples(current.get("examples", []), item.get("examples", []), day)
            current["display_size"] = round(44 + (current["importance"] * 92), 2)
            nodes[node_id] = current

            for target_label, relation in self._knowledge_relations(item):
                target_id = _safe_node_id("kp", target_label)
                self._touch_edge(edges, (node_id, target_id, relation), day)

        graph["nodes"], graph["archived_nodes"], graph["focus_node_ids"] = self._rebalance_graph_nodes(
            "knowledge",
            list(nodes.values()),
            list(archived.values()),
            day,
        )
        visible_ids = {item["id"] for item in graph["nodes"]}
        active_ids = {item["id"] for item in graph["nodes"] if item.get("status") == "active"}
        graph["edges"] = [
            {
                **edge,
                "status": (
                    "active"
                    if edge["source"] in active_ids and edge["target"] in active_ids
                    else "candidate"
                ),
            }
            for edge in edges.values()
            if edge["source"] in visible_ids and edge["target"] in visible_ids and edge["source"] != edge["target"]
        ]
        graph["stats"] = {
            "active": len(active_ids),
            "candidate": sum(1 for item in graph["nodes"] if item.get("status") == "candidate"),
            "archived": len(graph["archived_nodes"]),
        }
        self._save_graph(self.knowledge_graph_file, graph)

    def _knowledge_relations(self, item: dict[str, Any]) -> list[tuple[str, str]]:
        relations: list[tuple[str, str]] = []
        origin = _as_text(item.get("label")).strip().casefold()
        for label in item.get("prerequisites", []):
            if label.strip().casefold() != origin:
                relations.append((label, "prerequisite"))
        for label in item.get("similar_points", []):
            if label.strip().casefold() != origin:
                relations.append((label, "similar"))
        for label in item.get("contains_points", []):
            if label.strip().casefold() != origin:
                relations.append((label, "contains"))
        for label in item.get("related_points", []):
            if label.strip().casefold() != origin:
                relations.append((label, "related"))
        return relations

    def _update_error_graph(self, day: date, items: list[dict[str, Any]]) -> None:
        graph = self._load_graph(self.error_graph_file, "error")
        nodes = {
            item["id"]: dict(item)
            for item in graph["nodes"]
            if isinstance(item, dict) and item.get("id")
        }
        archived = {
            item["id"]: dict(item)
            for item in graph.get("archived_nodes", [])
            if isinstance(item, dict) and item.get("id")
        }
        edges = {
            (edge["source"], edge["target"], edge["relation"]): dict(edge)
            for edge in graph["edges"]
            if isinstance(edge, dict)
            and edge.get("source")
            and edge.get("target")
            and edge.get("relation")
        }

        for item in items:
            node_id = _safe_node_id("err", item["label"])
            current = nodes.get(node_id) or archived.pop(node_id, None) or {
                "id": node_id,
                "type": "error_pattern",
                "label": item["label"],
                "error_count": 0,
                "time_points": [],
                "examples": [],
                "status": "candidate",
            }
            already_seen_today = day.isoformat() in current.get("time_points", [])
            current["label"] = item["label"]
            current["severity"] = max(_clamp(current.get("severity"), 0.0), item["severity"])
            current["error_count"] = int(current.get("error_count", 0)) + (0 if already_seen_today else 1)
            current["repeated"] = bool(item.get("repeated") or current["error_count"] > 1)
            current["first_seen"] = current.get("first_seen") or day.isoformat()
            current["last_seen"] = day.isoformat()
            current["status"] = current.get("status", "candidate")
            current["notes"] = _join_notes(current.get("notes"), item.get("notes"))
            current["related_knowledge_points"] = _dedupe_texts(
                [*current.get("related_knowledge_points", []), *item.get("related_knowledge_points", [])],
                limit=10,
            )
            current["classic_example"] = _prefer_text(item.get("classic_example"), current.get("classic_example"))
            current["correction_suggestions"] = _dedupe_texts(
                [*current.get("correction_suggestions", []), *item.get("correction_suggestions", [])],
                limit=8,
            )
            current["time_points"] = _dedupe_texts([*current.get("time_points", []), day.isoformat()], limit=12)
            current["examples"] = self._merge_examples(current.get("examples", []), item.get("examples", []), day)
            score = min(1.0, 0.55 * current["severity"] + 0.12 * current["error_count"])
            current["display_size"] = round(44 + (score * 92), 2)
            nodes[node_id] = current

            for knowledge_label in current.get("related_knowledge_points", []):
                knowledge_id = _safe_node_id("kp", knowledge_label)
                self._touch_edge(edges, (node_id, knowledge_id, "corresponds_to"), day)
            for similar_label in item.get("similar_errors", []):
                similar_id = _safe_node_id("err", similar_label)
                if similar_id == node_id:
                    continue
                self._touch_edge(edges, (node_id, similar_id, "similar_error"), day)

        graph["nodes"], graph["archived_nodes"], graph["focus_node_ids"] = self._rebalance_graph_nodes(
            "error",
            list(nodes.values()),
            list(archived.values()),
            day,
        )
        visible_ids = {item["id"] for item in graph["nodes"]}
        active_ids = {item["id"] for item in graph["nodes"] if item.get("status") == "active"}
        graph["edges"] = [
            {
                **edge,
                "status": (
                    "active"
                    if edge["source"] in active_ids and (
                        edge["target"].startswith("kp:") or edge["target"] in active_ids
                    )
                    else "candidate"
                ),
            }
            for edge in edges.values()
            if edge["source"] in visible_ids and (
                edge["target"].startswith("kp:") or edge["target"] in visible_ids
            ) and edge["source"] != edge["target"]
        ]
        graph["stats"] = {
            "active": len(active_ids),
            "candidate": sum(1 for item in graph["nodes"] if item.get("status") == "candidate"),
            "archived": len(graph["archived_nodes"]),
        }
        self._save_graph(self.error_graph_file, graph)

    def graph_cleanup_candidates(self, kind: str, *, limit: int = 18) -> list[dict[str, Any]]:
        path = self.knowledge_graph_file if kind == "knowledge" else self.error_graph_file
        graph = self._load_graph(path, kind)
        nodes = [
            item for item in graph.get("nodes", [])
            if isinstance(item, dict) and item.get("status") in {"active", "candidate"}
        ]
        today = datetime.now().date()
        ranked = sorted(
            nodes,
            key=lambda item: (self._graph_score(kind, item, today), item.get("last_seen", "")),
            reverse=True,
        )
        return [
            {
                "label": _as_text(item.get("label")).strip(),
                "status": _as_text(item.get("status")).strip() or "candidate",
                "notes": _as_text(item.get("notes")).strip(),
                "last_seen": item.get("last_seen"),
                "classic_example": _as_text(item.get("classic_example")).strip(),
                "examples": _coerce_text_list(item.get("examples"), limit=3),
                "related_knowledge_points": _coerce_text_list(item.get("related_knowledge_points"), limit=4),
                "correction_suggestions": _coerce_text_list(item.get("correction_suggestions"), limit=4),
            }
            for item in ranked[:limit]
            if _as_text(item.get("label")).strip()
        ]

    def apply_graph_cleanup_plan(
        self,
        day: date,
        *,
        knowledge_merges: list[dict[str, Any]] | None = None,
        error_merges: list[dict[str, Any]] | None = None,
        error_refinements: list[dict[str, Any]] | None = None,
    ) -> None:
        if knowledge_merges:
            self._merge_graph_nodes(self.knowledge_graph_file, "knowledge", knowledge_merges, day)
        if error_merges:
            self._merge_graph_nodes(self.error_graph_file, "error", error_merges, day)
        if error_refinements:
            self._refine_error_graph_nodes(day, error_refinements)

    def _refine_error_graph_nodes(
        self,
        day: date,
        refinements: list[dict[str, Any]],
    ) -> None:
        graph = self._load_graph(self.error_graph_file, "error")
        visible = {
            item["id"]: dict(item)
            for item in graph.get("nodes", [])
            if isinstance(item, dict) and item.get("id")
        }
        archived = {
            item["id"]: dict(item)
            for item in graph.get("archived_nodes", [])
            if isinstance(item, dict) and item.get("id")
        }
        edges = {
            (edge["source"], edge["target"], edge["relation"]): dict(edge)
            for edge in graph.get("edges", [])
            if isinstance(edge, dict)
            and edge.get("source")
            and edge.get("target")
            and edge.get("relation")
        }

        def rebuild_label_map() -> dict[str, str]:
            return {
                _as_text(item.get("label")).strip().casefold(): item["id"]
                for item in [*visible.values(), *archived.values()]
                if _as_text(item.get("label")).strip()
            }

        label_map = rebuild_label_map()
        for refinement in refinements:
            if not isinstance(refinement, dict):
                continue

            source_label = _as_text(refinement.get("from_label") or refinement.get("source")).strip()
            target_label = _as_text(refinement.get("into_label") or refinement.get("target")).strip() or source_label
            if not source_label or not target_label:
                continue

            source_id = label_map.get(source_label.casefold())
            if not source_id:
                continue

            source_was_visible = source_id in visible
            source_node = visible.pop(source_id, None) or archived.pop(source_id, None)
            if not source_node:
                label_map = rebuild_label_map()
                continue

            note_text = _as_text(refinement.get("notes")).strip()
            classic_example = _as_text(refinement.get("classic_example")).strip()
            target_id = _safe_node_id("err", target_label)
            target_node = visible.get(target_id) or archived.get(target_id)

            if target_node and target_id != source_id:
                merged = self._merge_node_payload("error", target_node, source_node, day)
                merged["label"] = target_label
                merged["notes"] = _join_notes(merged.get("notes"), note_text)
                merged["classic_example"] = _prefer_text(classic_example, merged.get("classic_example"))
                if target_id in visible:
                    visible[target_id] = merged
                else:
                    archived[target_id] = merged
            else:
                renamed = dict(source_node)
                renamed["id"] = target_id
                renamed["label"] = target_label
                renamed["notes"] = _join_notes(renamed.get("notes"), note_text)
                renamed["classic_example"] = _prefer_text(classic_example, renamed.get("classic_example"))
                if source_was_visible or source_node.get("status") != "archived":
                    visible[target_id] = renamed
                else:
                    archived[target_id] = renamed

            rewritten: dict[tuple[str, str, str], dict[str, Any]] = {}
            for edge in edges.values():
                next_source = target_id if edge["source"] == source_id else edge["source"]
                next_target = target_id if edge["target"] == source_id else edge["target"]
                if next_source == next_target:
                    continue
                key = (next_source, next_target, edge["relation"])
                candidate = {**edge, "source": next_source, "target": next_target}
                existing = rewritten.get(key)
                if existing is None:
                    rewritten[key] = candidate
                    continue
                existing["occurrences"] = max(
                    int(existing.get("occurrences", 0)),
                    int(candidate.get("occurrences", 0)),
                )
                existing["strength"] = max(
                    _clamp(existing.get("strength"), 0.35),
                    _clamp(candidate.get("strength"), 0.35),
                )
                existing["updated_at"] = max(
                    _as_text(existing.get("updated_at")),
                    _as_text(candidate.get("updated_at")),
                )
            edges = rewritten
            label_map = rebuild_label_map()

        graph["nodes"], graph["archived_nodes"], graph["focus_node_ids"] = self._rebalance_graph_nodes(
            "error",
            list(visible.values()),
            list(archived.values()),
            day,
        )
        visible_ids = {item["id"] for item in graph["nodes"]}
        active_ids = {item["id"] for item in graph["nodes"] if item.get("status") == "active"}
        graph["edges"] = [
            {
                **edge,
                "status": (
                    "active"
                    if edge["source"] in active_ids and (
                        edge["target"].startswith("kp:") or edge["target"] in active_ids
                    )
                    else "candidate"
                ),
            }
            for edge in edges.values()
            if edge["source"] in visible_ids and (
                edge["target"].startswith("kp:") or edge["target"] in visible_ids
            ) and edge["source"] != edge["target"]
        ]
        graph["stats"] = {
            "active": len(active_ids),
            "candidate": sum(1 for item in graph["nodes"] if item.get("status") == "candidate"),
            "archived": len(graph["archived_nodes"]),
        }
        self._save_graph(self.error_graph_file, graph)

    def _merge_graph_nodes(
        self,
        path: Path,
        kind: str,
        merges: list[dict[str, Any]],
        day: date,
    ) -> None:
        graph = self._load_graph(path, kind)
        visible = {
            item["id"]: dict(item)
            for item in graph.get("nodes", [])
            if isinstance(item, dict) and item.get("id")
        }
        archived = {
            item["id"]: dict(item)
            for item in graph.get("archived_nodes", [])
            if isinstance(item, dict) and item.get("id")
        }
        label_map = {
            _as_text(item.get("label")).strip().casefold(): item["id"]
            for item in [*visible.values(), *archived.values()]
            if _as_text(item.get("label")).strip()
        }
        edges = {
            (edge["source"], edge["target"], edge["relation"]): dict(edge)
            for edge in graph.get("edges", [])
            if isinstance(edge, dict)
            and edge.get("source")
            and edge.get("target")
            and edge.get("relation")
        }

        for merge in merges:
            if not isinstance(merge, dict):
                continue
            source_label = _as_text(merge.get("from_label") or merge.get("source")).strip()
            target_label = _as_text(merge.get("into_label") or merge.get("target")).strip()
            if not source_label or not target_label or source_label.casefold() == target_label.casefold():
                continue
            source_id = label_map.get(source_label.casefold())
            target_id = label_map.get(target_label.casefold())
            if not source_id or not target_id or source_id == target_id:
                continue

            source = visible.pop(source_id, None) or archived.pop(source_id, None)
            target = visible.get(target_id) or archived.get(target_id)
            if not source or not target:
                continue

            merged = self._merge_node_payload(kind, target, source, day)
            if target_id in visible:
                visible[target_id] = merged
            else:
                archived[target_id] = merged

            rewritten: dict[tuple[str, str, str], dict[str, Any]] = {}
            for edge in edges.values():
                source_edge = target_id if edge["source"] == source_id else edge["source"]
                target_edge = target_id if edge["target"] == source_id else edge["target"]
                if source_edge == target_edge:
                    continue
                key = (source_edge, target_edge, edge["relation"])
                candidate = {**edge, "source": source_edge, "target": target_edge}
                existing = rewritten.get(key)
                if existing is None:
                    rewritten[key] = candidate
                    continue
                existing["occurrences"] = max(int(existing.get("occurrences", 0)), int(candidate.get("occurrences", 0)))
                existing["strength"] = max(_clamp(existing.get("strength"), 0.35), _clamp(candidate.get("strength"), 0.35))
                existing["updated_at"] = max(_as_text(existing.get("updated_at")), _as_text(candidate.get("updated_at")))
            edges = rewritten

        graph["nodes"], graph["archived_nodes"], graph["focus_node_ids"] = self._rebalance_graph_nodes(
            kind,
            list(visible.values()),
            list(archived.values()),
            day,
        )
        visible_ids = {item["id"] for item in graph["nodes"]}
        active_ids = {item["id"] for item in graph["nodes"] if item.get("status") == "active"}
        graph["edges"] = [
            {
                **edge,
                "status": (
                    "active"
                    if edge["source"] in active_ids and (
                        (kind == "knowledge" and edge["target"] in active_ids)
                        or (
                            kind == "error"
                            and (edge["target"].startswith("kp:") or edge["target"] in active_ids)
                        )
                    )
                    else "candidate"
                ),
            }
            for edge in edges.values()
            if edge["source"] in visible_ids and (
                (kind == "knowledge" and edge["target"] in visible_ids)
                or (
                    kind == "error"
                    and (edge["target"].startswith("kp:") or edge["target"] in visible_ids)
                )
            ) and edge["source"] != edge["target"]
        ]
        graph["stats"] = {
            "active": len(active_ids),
            "candidate": sum(1 for item in graph["nodes"] if item.get("status") == "candidate"),
            "archived": len(graph["archived_nodes"]),
        }
        self._save_graph(path, graph)

    def _merge_node_payload(
        self,
        kind: str,
        target: dict[str, Any],
        source: dict[str, Any],
        day: date,
    ) -> dict[str, Any]:
        merged = dict(target)
        merged["notes"] = _join_notes(target.get("notes"), source.get("notes"))
        merged["time_points"] = _dedupe_texts([*target.get("time_points", []), *source.get("time_points", [])], limit=12)
        merged["examples"] = self._merge_examples(target.get("examples", []), source.get("examples", []), day)
        merged["first_seen"] = min(_as_text(target.get("first_seen")), _as_text(source.get("first_seen"))) or target.get("first_seen") or source.get("first_seen")
        merged["last_seen"] = max(_as_text(target.get("last_seen")), _as_text(source.get("last_seen"))) or target.get("last_seen") or source.get("last_seen")
        if kind == "knowledge":
            merged["occurrences"] = int(target.get("occurrences", 0)) + int(source.get("occurrences", 0))
            merged["risk"] = max(_clamp(target.get("risk"), 0.0), _clamp(source.get("risk"), 0.0))
            merged["mastery"] = _blend(target.get("mastery"), source.get("mastery"), default=_clamp(target.get("mastery"), 0.4))
            merged["importance"] = max(_clamp(target.get("importance"), 0.0), _clamp(source.get("importance"), 0.0))
            merged["prerequisites"] = _dedupe_texts([*target.get("prerequisites", []), *source.get("prerequisites", [])], limit=8)
            merged["similar_points"] = _dedupe_texts([*target.get("similar_points", []), *source.get("similar_points", [])], limit=8)
            merged["contains_points"] = _dedupe_texts([*target.get("contains_points", []), *source.get("contains_points", [])], limit=8)
            merged["related_points"] = _dedupe_texts([*target.get("related_points", []), *source.get("related_points", [])], limit=8)
            merged["display_size"] = round(44 + (merged["importance"] * 92), 2)
        else:
            merged["error_count"] = int(target.get("error_count", 0)) + int(source.get("error_count", 0))
            merged["severity"] = max(_clamp(target.get("severity"), 0.0), _clamp(source.get("severity"), 0.0))
            merged["repeated"] = bool(target.get("repeated") or source.get("repeated") or merged["error_count"] > 1)
            merged["classic_example"] = _prefer_text(target.get("classic_example"), source.get("classic_example"))
            merged["related_knowledge_points"] = _dedupe_texts([*target.get("related_knowledge_points", []), *source.get("related_knowledge_points", [])], limit=10)
            merged["similar_errors"] = _dedupe_texts([*target.get("similar_errors", []), *source.get("similar_errors", [])], limit=8)
            merged["correction_suggestions"] = _dedupe_texts([*target.get("correction_suggestions", []), *source.get("correction_suggestions", [])], limit=8)
            score = min(1.0, 0.55 * merged["severity"] + 0.12 * merged["error_count"])
            merged["display_size"] = round(44 + (score * 92), 2)
        return merged

    def _merge_examples(self, existing: list[Any], incoming: list[Any], day: date) -> list[dict[str, str]]:
        cutoff = day - timedelta(days=_GRAPH_EXAMPLE_RETENTION_DAYS)
        pool: list[dict[str, str]] = []
        for raw in [*existing, *incoming]:
            if isinstance(raw, dict):
                text = _as_text(raw.get("text")).strip()
                observed = _parse_timestamp(raw.get("timestamp")).date()
            else:
                text = _as_text(raw).strip()
                observed = day
            if not text or observed < cutoff:
                continue
            pool.append({"text": text, "timestamp": observed.isoformat()})

        deduped: dict[str, dict[str, str]] = {}
        for item in sorted(pool, key=lambda value: value["timestamp"], reverse=True):
            deduped.setdefault(item["text"].casefold(), item)
        return list(deduped.values())[:_MAX_GRAPH_EXAMPLES]

    def _prune_graph_nodes(
        self,
        active_nodes: list[dict[str, Any]],
        archived_nodes: list[dict[str, Any]],
        today: date,
        *,
        comparator: Callable[[dict[str, Any]], bool],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        threshold = today - timedelta(days=_LOW_SIGNAL_DAYS)
        still_active: list[dict[str, Any]] = []
        archived_map = {
            item["id"]: dict(item)
            for item in archived_nodes
            if isinstance(item, dict) and item.get("id")
        }

        for node in active_nodes:
            last_seen = _parse_timestamp(node.get("last_seen")).date()
            if last_seen <= threshold and comparator(node):
                node["status"] = "archived"
                archived_map[node["id"]] = node
                continue
            node["status"] = "active"
            still_active.append(node)

        sorted_active = sorted(
            still_active,
            key=lambda node: (
                _clamp(node.get("importance"), 0.0, high=2.0),
                _clamp(node.get("severity"), 0.0, high=2.0),
                _clamp(node.get("risk"), 0.0, high=2.0),
                int(node.get("error_count", 0)),
                int(node.get("occurrences", 0)),
                node.get("last_seen", ""),
            ),
            reverse=True,
        )
        sorted_archived = sorted(
            archived_map.values(),
            key=lambda node: node.get("last_seen", ""),
            reverse=True,
        )
        return sorted_active, sorted_archived[:120]

    async def _refresh_weekly_plan(self, day: date, provider: LLMProvider, model: str) -> None:
        await self.ensure_weekly_summary(day, provider, model)

    async def ensure_weekly_summary(
        self,
        day: date,
        provider: LLMProvider,
        model: str,
    ) -> str | None:
        daily_payloads: list[dict[str, Any]] = []
        for offset in range(_MAX_WEEKLY_DAYS - 1, -1, -1):
            current_day = day - timedelta(days=offset)
            payload = self._load_daily_payload(current_day)
            if payload is not None:
                daily_payloads.append(payload)

        if not daily_payloads:
            return None

        plan_markdown = await self._generate_weekly_plan(day, daily_payloads, provider, model)
        week_root = ensure_dir(self.weekly_memory_dir / _week_file_stem(day))
        weekly_file = week_root / f"{_week_file_stem(day)}.md"
        weekly_file.write_text(plan_markdown, encoding="utf-8")
        return plan_markdown

    def _load_daily_payload(self, day: date) -> dict[str, Any] | None:
        _, _, json_file, _ = self._day_paths(day)
        payload = _load_json(json_file, None)
        return payload if isinstance(payload, dict) else None

    async def _generate_weekly_plan(
        self,
        day: date,
        daily_payloads: list[dict[str, Any]],
        provider: LLMProvider,
        model: str,
    ) -> str:
        knowledge_top = self.top_graph_nodes("knowledge", limit=4)
        error_top = self.top_graph_nodes("error", limit=4)
        prompt = "\n\n".join([
            "Read the last 7 daily learning summaries and write a concise weekly summary plus next week's study plan in markdown.",
            "Use these exact sections in Chinese:",
            "1. 本周目标",
            "2. 每天建议主题",
            "3. 优先复习知识点",
            "4. 重点纠错方向",
            "5. 推荐练习量",
            "6. 难度调整建议",
            "Daily payloads:",
            json.dumps(daily_payloads, ensure_ascii=False, indent=2),
            "Knowledge graph highlights:",
            json.dumps(knowledge_top, ensure_ascii=False, indent=2),
            "Error graph highlights:",
            json.dumps(error_top, ensure_ascii=False, indent=2),
        ])

        try:
            response = await provider.chat_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a study-planning agent for a middle/high-school math tutor. "
                            "Write practical Chinese markdown with clear headings, short bullets, "
                            "and concrete weekly guidance."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                model=model,
            )
            content = (response.content or "").strip()
            if content:
                return content
        except Exception:
            logger.exception("Weekly learning plan generation failed for {}", day.isoformat())

        return self._fallback_weekly_plan(day, daily_payloads, knowledge_top, error_top)

    def _fallback_weekly_plan(
        self,
        day: date,
        daily_payloads: list[dict[str, Any]],
        knowledge_top: list[dict[str, Any]],
        error_top: list[dict[str, Any]],
    ) -> str:
        start_day = day - timedelta(days=_MAX_WEEKLY_DAYS - 1)
        suggestions = _dedupe_texts(
            [
                suggestion
                for payload in daily_payloads
                for suggestion in payload.get("tomorrow_study_suggestions", [])
            ],
            limit=6,
        )
        return "\n".join([
            f"# 周学习计划 - {start_day.isoformat()} to {day.isoformat()}",
            "",
            "## 本周目标",
            f"- 基于最近 {len(daily_payloads)} 天的学习摘要，优先稳住高风险知识点并修正重复错误。",
            "",
            "## 每天建议主题",
            *(suggestions and [f"- {item}" for item in suggestions] or ["- 每天安排 1 个主知识点复盘 + 1 组错题回顾。"]),
            "",
            "## 优先复习知识点",
            *(
                [f"- 复习知识点：{item['label']}" for item in knowledge_top]
                or ["- 复习最近一周中反复出现的核心知识点。"]
            ),
            "",
            "## 重点纠错方向",
            *(
                [f"- 修正错误模式：{item['label']}" for item in error_top]
                or ["- 整理重复错误并补充对应纠错步骤。"]
            ),
            "",
            "## 推荐练习量",
            "- 每天 6 到 10 题，先基础巩固，再做 2 到 3 题变式提升。",
            "",
            "## 难度调整建议",
            "- 如果连续两天正确率低于 70%，先降低难度并补基础；如果正确率稳定在 85% 以上，再增加综合题比例。",
        ])

    def _latest_daily_payload(self) -> dict[str, Any] | None:
        candidates: list[tuple[date, dict[str, Any]]] = []
        for path in self.daily_memory_dir.glob("*/*.json"):
            payload = _load_json(path, None)
            if not isinstance(payload, dict):
                continue
            try:
                day = date.fromisoformat(str(payload.get("date")))
            except ValueError:
                continue
            candidates.append((day, payload))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _latest_weekly_markdown(self) -> str:
        candidates = sorted(self.weekly_memory_dir.glob("*/*.md"), key=lambda path: path.name, reverse=True)
        if not candidates:
            return ""
        return candidates[0].read_text(encoding="utf-8")

    def top_graph_nodes(self, kind: str, *, limit: int = _MAX_GRAPH_CONTEXT_ITEMS) -> list[dict[str, Any]]:
        path = self.knowledge_graph_file if kind == "knowledge" else self.error_graph_file
        graph = self._load_graph(path, kind)
        active = [
            item for item in graph.get("nodes", [])
            if isinstance(item, dict) and item.get("status") == "active"
        ]
        candidate = [
            item for item in graph.get("nodes", [])
            if isinstance(item, dict) and item.get("status") == "candidate"
        ]
        nodes = active or candidate
        ranked = sorted(
            nodes,
            key=lambda item: (
                _clamp(item.get("importance"), 0.0, high=2.0),
                _clamp(item.get("severity"), 0.0, high=2.0),
                _clamp(item.get("risk"), 0.0, high=2.0),
                int(item.get("error_count", 0)),
                int(item.get("occurrences", 0)),
                item.get("last_seen", ""),
            ),
            reverse=True,
        )
        return ranked[:limit]

    @staticmethod
    def _graph_node_text(node: dict[str, Any]) -> str:
        parts = [
            _as_text(node.get("label")),
            _as_text(node.get("notes")),
            _as_text(node.get("classic_example")),
            " ".join(_coerce_text_list(node.get("related_knowledge_points"), limit=8)),
            " ".join(_coerce_text_list(node.get("correction_suggestions"), limit=8)),
        ]
        for example in node.get("examples", []) or []:
            if isinstance(example, dict):
                parts.append(_as_text(example.get("text")))
            else:
                parts.append(_as_text(example))
        return " ".join(part for part in parts if part).casefold()

    def find_relevant_graph_nodes(
        self,
        kind: str,
        query: str,
        *,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        path = self.knowledge_graph_file if kind == "knowledge" else self.error_graph_file
        graph = self._load_graph(path, kind)
        ranked = sorted(
            [
                item for item in graph.get("nodes", [])
                if isinstance(item, dict) and item.get("status") in {"active", "candidate"}
            ],
            key=lambda item: (
                1 if item.get("status") == "active" else 0,
                _clamp(item.get("importance"), 0.0, high=2.0),
                _clamp(item.get("severity"), 0.0, high=2.0),
                _clamp(item.get("risk"), 0.0, high=2.0),
                int(item.get("error_count", 0)),
                int(item.get("occurrences", 0)),
                item.get("last_seen", ""),
            ),
            reverse=True,
        )[:50]
        if not query.strip():
            return ranked[:limit]

        query_text = query.casefold()
        terms = _query_terms(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for node in ranked:
            label = _as_text(node.get("label")).strip()
            haystack = self._graph_node_text(node)
            score = 0.0
            if label:
                lowered = label.casefold()
                if lowered in query_text or query_text[: min(len(query_text), 24)] in lowered:
                    score += 8.0
                max_width = min(6, len(label))
                for width in range(max_width, 1, -1):
                    matched = False
                    for start in range(0, len(label) - width + 1):
                        fragment = label[start : start + width].casefold()
                        if fragment and fragment in query_text:
                            score += width * 1.2
                            matched = True
                            break
                    if matched:
                        break
            for term in terms:
                lowered = term.casefold()
                if label and lowered in label.casefold():
                    score += 4.0
                elif lowered in haystack:
                    score += 1.5
            score += _clamp(node.get("importance"), 0.0, high=2.0)
            score += _clamp(node.get("severity"), 0.0, high=2.0)
            score += _clamp(node.get("risk"), 0.0, high=2.0)
            if score > 0:
                scored.append((score, node))

        if not scored:
            return ranked[:limit]

        scored.sort(key=lambda item: item[0], reverse=True)
        return [node for _, node in scored[:limit]]

    @staticmethod
    def _compact_markdown(markdown: str, *, max_chars: int = _MAX_MEMORY_CONTEXT_CHARS) -> str:
        cleaned = re.sub(r"\n{3,}", "\n\n", (markdown or "").strip())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[:max_chars].rstrip() + "\n..."

    def build_prompt_context(
        self,
        query: str,
        *,
        knowledge_limit: int = 4,
        error_limit: int = 4,
    ) -> str:
        latest_daily = self._latest_daily_payload()
        latest_weekly = self._latest_weekly_markdown()
        knowledge_nodes = self.find_relevant_graph_nodes("knowledge", query, limit=knowledge_limit)
        error_nodes = self.find_relevant_graph_nodes("error", query, limit=error_limit)

        if not latest_daily and not latest_weekly and not knowledge_nodes and not error_nodes:
            return ""

        lines = ["# Learning Memory Retrieval", ""]
        if latest_daily:
            lines.extend([
                f"## 最近每日总结 ({latest_daily.get('date', '')})",
                _as_text(latest_daily.get("learning_status_summary")).strip() or "暂无学习状态总结。",
                "",
                "### 明日建议",
                *(
                    [f"- {item}" for item in latest_daily.get("tomorrow_study_suggestions", [])]
                    or ["- 暂无建议。"]
                ),
                "",
            ])
        if latest_weekly:
            lines.extend([
                "## 最近每周计划",
                self._compact_markdown(latest_weekly),
                "",
            ])
        if knowledge_nodes:
            lines.extend([
                "## 相关知识点图谱",
                *[
                    f"- {node.get('label', '')} | 风险 {_clamp(node.get('risk'), 0.0):.2f} | 掌握度 {_clamp(node.get('mastery'), 0.0):.2f} | 重要度 {_clamp(node.get('importance'), 0.0):.2f}"
                    + (f" | {node.get('notes')}" if node.get("notes") else "")
                    for node in knowledge_nodes
                ],
                "",
            ])
        if error_nodes:
            lines.extend([
                "## 相关错题图谱",
                *[
                    f"- {node.get('label', '')} | 严重度 {_clamp(node.get('severity'), 0.0):.2f} | 次数 {int(node.get('error_count', 0) or 0)}"
                    + (f" | 纠正: {', '.join(_coerce_text_list(node.get('correction_suggestions'), limit=2))}" if node.get("correction_suggestions") else "")
                    + (f" | 例题: {_as_text(node.get('classic_example')).strip()}" if node.get("classic_example") else "")
                    for node in error_nodes
                ],
            ])
        return "\n".join(lines).strip()

    def _build_memory_snapshot(self) -> str:
        latest_daily = self._latest_daily_payload()
        latest_weekly = self._latest_weekly_markdown()
        knowledge_top = self.top_graph_nodes("knowledge")
        error_top = self.top_graph_nodes("error")

        if not latest_daily and not latest_weekly and not knowledge_top and not error_top:
            return ""

        lines = ["# Learning Memory Snapshot", ""]
        if latest_daily:
            lines.extend([
                f"## Latest Daily Summary ({latest_daily['date']})",
                latest_daily["learning_status_summary"],
                "",
                "### Tomorrow Study Suggestions",
                *(
                    [f"- {item}" for item in latest_daily.get("tomorrow_study_suggestions", [])]
                    or ["- 暂无建议。"]
                ),
                "",
            ])
        if latest_weekly:
            lines.extend([
                "## Weekly Study Plan",
                latest_weekly.strip(),
                "",
            ])
        lines.extend([
            "## Knowledge Graph Highlights",
            *(
                [
                    f"- {item['label']} | 风险 {item.get('risk', 0):.2f} | 掌握度 {item.get('mastery', 0):.2f} | 重要度 {item.get('importance', 0):.2f}"
                    for item in knowledge_top
                ]
                or ["- 暂无知识点图谱。"]
            ),
            "",
            "## Error Graph Highlights",
            *(
                [
                    f"- {item['label']} | 严重度 {item.get('severity', 0):.2f} | 次数 {item.get('error_count', 0)}"
                    for item in error_top
                ]
                or ["- 暂无错题图谱。"]
            ),
        ])
        return "\n".join(lines).strip() + "\n"


class MemoryConsolidator:
    """Owns consolidation policy, locking, and session offset updates."""

    _MAX_CONSOLIDATION_ROUNDS = 5
    _SAFETY_BUFFER = 1024

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider,
        model: str,
        sessions: SessionManager,
        context_window_tokens: int,
        build_messages: Callable[..., list[dict[str, Any]]],
        get_tool_definitions: Callable[[], list[dict[str, Any]]],
        max_completion_tokens: int = 4096,
    ):
        self.store = MemoryStore(workspace)
        self.provider = provider
        self.model = model
        self.sessions = sessions
        self.context_window_tokens = context_window_tokens
        self.max_completion_tokens = max_completion_tokens
        self._build_messages = build_messages
        self._get_tool_definitions = get_tool_definitions
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    def get_lock(self, session_key: str) -> asyncio.Lock:
        return self._locks.setdefault(session_key, asyncio.Lock())

    async def consolidate_messages(
        self,
        messages: list[dict[str, object]],
        *,
        session_key: str | None = None,
    ) -> bool:
        return await self.store.consolidate(
            list(messages),
            self.provider,
            self.model,
            session_key=session_key,
        )

    def pick_consolidation_boundary(
        self,
        session: Session,
        tokens_to_remove: int,
    ) -> tuple[int, int] | None:
        start = session.last_consolidated
        if start >= len(session.messages) or tokens_to_remove <= 0:
            return None

        removed_tokens = 0
        last_boundary: tuple[int, int] | None = None
        for idx in range(start, len(session.messages)):
            message = session.messages[idx]
            if idx > start and message.get("role") == "user":
                last_boundary = (idx, removed_tokens)
                if removed_tokens >= tokens_to_remove:
                    return last_boundary
            removed_tokens += estimate_message_tokens(message)
        return last_boundary

    def estimate_session_prompt_tokens(self, session: Session) -> tuple[int, str]:
        history = session.get_history(max_messages=0)
        channel, chat_id = (session.key.split(":", 1) if ":" in session.key else (None, None))
        probe_messages = self._build_messages(
            history=history,
            current_message="[token-probe]",
            channel=channel,
            chat_id=chat_id,
        )
        return estimate_prompt_tokens_chain(
            self.provider,
            self.model,
            probe_messages,
            self._get_tool_definitions(),
        )

    async def archive_messages(
        self,
        messages: list[dict[str, object]],
        *,
        session_key: str | None = None,
    ) -> bool:
        if not messages:
            return True
        return await self.consolidate_messages(messages, session_key=session_key)

    async def maybe_consolidate_by_tokens(self, session: Session) -> None:
        if not session.messages or self.context_window_tokens <= 0:
            return

        lock = self.get_lock(session.key)
        async with lock:
            budget = self.context_window_tokens - self.max_completion_tokens - self._SAFETY_BUFFER
            target = budget // 2
            estimated, source = self.estimate_session_prompt_tokens(session)
            if estimated <= 0:
                return
            if estimated < budget:
                logger.debug(
                    "Token consolidation idle {}: {}/{} via {}",
                    session.key,
                    estimated,
                    self.context_window_tokens,
                    source,
                )
                return

            for round_num in range(self._MAX_CONSOLIDATION_ROUNDS):
                if estimated <= target:
                    return

                boundary = self.pick_consolidation_boundary(session, max(1, estimated - target))
                if boundary is None:
                    logger.debug(
                        "Token consolidation: no safe boundary for {} (round {})",
                        session.key,
                        round_num,
                    )
                    return

                end_idx = boundary[0]
                chunk = session.messages[session.last_consolidated:end_idx]
                if not chunk:
                    return

                logger.info(
                    "Token consolidation round {} for {}: {}/{} via {}, chunk={} msgs",
                    round_num,
                    session.key,
                    estimated,
                    self.context_window_tokens,
                    source,
                    len(chunk),
                )
                if not await self.consolidate_messages(chunk, session_key=session.key):
                    return
                session.last_consolidated = end_idx
                self.sessions.save(session)

                estimated, source = self.estimate_session_prompt_tokens(session)
                if estimated <= 0:
                    return
