"""Runtime memory retrieval and live graph updates for MathClaw."""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from loguru import logger

from .memory import MemoryStore, _week_file_stem

if TYPE_CHECKING:
    from ..providers.base import LLMProvider, LLMResponse
    from ..session.manager import SessionManager


_TURN_SIGNAL_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_turn_learning_signals",
            "description": "Extract stable knowledge-point and error-pattern updates from one tutoring turn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_updates": {
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
                    "error_updates": {
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
                                "related_knowledge_points": {"type": "array", "items": {"type": "string"}},
                                "similar_errors": {"type": "array", "items": {"type": "string"}},
                                "correction_suggestions": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["label"],
                        },
                    },
                },
                "required": ["knowledge_updates", "error_updates"],
            },
        },
    }
]

_GRAPH_CLEANUP_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_graph_cleanup_plan",
            "description": "Merge only obvious duplicate or near-duplicate graph nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge_merges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_label": {"type": "string"},
                                "into_label": {"type": "string"},
                            },
                            "required": ["from_label", "into_label"],
                        },
                    },
                    "error_merges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_label": {"type": "string"},
                                "into_label": {"type": "string"},
                            },
                            "required": ["from_label", "into_label"],
                        },
                    },
                    "error_refinements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "from_label": {"type": "string"},
                                "into_label": {"type": "string"},
                                "classic_example": {"type": "string"},
                                "notes": {"type": "string"},
                            },
                            "required": ["from_label", "into_label"],
                        },
                    },
                },
                "required": ["knowledge_merges", "error_merges", "error_refinements"],
            },
        },
    }
]

_TURN_TOOL_CHOICE_MARKERS = (
    "tool_choice",
    "toolchoice",
    "does not support",
    'should be ["none", "auto"]',
)


def _is_tool_choice_unsupported(content: str | None) -> bool:
    text = (content or "").lower()
    return any(marker in text for marker in _TURN_TOOL_CHOICE_MARKERS)


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


def _trim_block(text: str | None, *, limit: int = 2400) -> str:
    content = (text or "").strip()
    if len(content) <= limit:
        return content
    return content[:limit].rstrip() + "\n..."


class MemoryRuntime:
    """Own live graph updates and retrieval-friendly memory refreshes."""

    _DAILY_REFRESH_INTERVAL_S = 300
    _WEEKLY_REFRESH_INTERVAL_S = 1800
    _GRAPH_CLEANUP_INTERVAL_S = 900

    def __init__(
        self,
        *,
        workspace: Path,
        provider: "LLMProvider",
        model: str,
        sessions: "SessionManager",
        timezone: str | None = None,
    ) -> None:
        self.store = MemoryStore(workspace)
        self.provider = provider
        self.model = model
        self.sessions = sessions
        self.timezone = ZoneInfo(timezone or "Asia/Shanghai")
        self._daily_locks: dict[date, asyncio.Lock] = {}
        self._weekly_locks: dict[date, asyncio.Lock] = {}
        self._last_daily_refresh: dict[date, float] = {}
        self._last_weekly_refresh: dict[date, float] = {}
        self._last_graph_cleanup_at = 0.0

    def build_context(self, query: str) -> str:
        return self.store.build_prompt_context(query)

    async def update_after_turn(
        self,
        *,
        session_key: str,
        user_text: str,
        assistant_text: str,
        attachment_context: str = "",
    ) -> None:
        if not user_text.strip() and not assistant_text.strip():
            return

        day = self._today()
        try:
            payload = await self._extract_turn_learning_signals(
                session_key=session_key,
                user_text=user_text,
                assistant_text=assistant_text,
                attachment_context=attachment_context,
            )
            if payload:
                self.store.apply_turn_graph_updates(
                    day,
                    knowledge_updates=payload.get("knowledge_updates") or [],
                    error_updates=payload.get("error_updates") or [],
                )
        except Exception:
            logger.exception("Failed to extract turn learning signals for {}", session_key)

        await self._maybe_refresh_daily(day)
        await self._maybe_refresh_weekly(day)
        await self._maybe_cleanup_graphs(day)

    async def _extract_turn_learning_signals(
        self,
        *,
        session_key: str,
        user_text: str,
        assistant_text: str,
        attachment_context: str,
    ) -> dict[str, Any] | None:
        prompt = "\n\n".join([
            "Extract stable learning signals from this MathClaw tutoring turn.",
            "Only include knowledge points and error patterns that are explicit or strongly implied.",
            "Prefer concise Chinese labels.",
            "Error-pattern labels must be generic reusable pattern names, not one-off题面碎片、变量名或式子片段。",
            "For each error pattern, provide one short classic_example that a student can recognize later.",
            "Keep both lists short (prefer <= 5 items each).",
            f"Session: {session_key}",
            "User Question:",
            _trim_block(user_text),
            "Attachment Context:",
            _trim_block(attachment_context),
            "Assistant Answer:",
            _trim_block(assistant_text),
        ])

        raw_payload: dict[str, Any] | None = None
        forced = {"type": "function", "function": {"name": "save_turn_learning_signals"}}
        try:
            response: "LLMResponse" = await self.provider.chat_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You extract structured learning signals for a middle/high-school math tutor. "
                            "Always call save_turn_learning_signals with concise, reusable graph updates. "
                            "Error labels must be generic pattern titles, and each error update should include one short classic_example."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                tools=_TURN_SIGNAL_TOOL,
                model=self.model,
                tool_choice=forced,
            )
            if response.finish_reason == "error" and _is_tool_choice_unsupported(response.content):
                response = await self.provider.chat_with_retry(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You extract structured learning signals for a middle/high-school math tutor. "
                                "Return concise JSON with knowledge_updates and error_updates. "
                                "Error labels must be generic pattern titles, and each error update should include one short classic_example."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    tools=_TURN_SIGNAL_TOOL,
                    model=self.model,
                    tool_choice="auto",
                )
            if response.has_tool_calls:
                raw_payload = _normalize_tool_args(response.tool_calls[0].arguments)
            if raw_payload is None:
                raw_payload = _extract_json_object(response.content)
        except Exception:
            logger.exception("Turn learning-signal extraction failed")
            return None

        if not isinstance(raw_payload, dict):
            return None
        return {
            "knowledge_updates": raw_payload.get("knowledge_updates") or [],
            "error_updates": raw_payload.get("error_updates") or [],
        }

    async def _maybe_cleanup_graphs(self, day: date) -> None:
        if time.monotonic() - self._last_graph_cleanup_at < self._GRAPH_CLEANUP_INTERVAL_S:
            return

        knowledge_nodes = self.store.graph_cleanup_candidates("knowledge")
        error_nodes = self.store.graph_cleanup_candidates("error")
        has_candidates = any(item.get("status") == "candidate" for item in [*knowledge_nodes, *error_nodes])
        has_refinement_targets = any(
            not str(item.get("classic_example") or "").strip()
            or any(char.isdigit() for char in str(item.get("label") or ""))
            for item in error_nodes
        )
        if not has_candidates and not has_refinement_targets:
            return

        plan = await self._extract_graph_cleanup_plan(knowledge_nodes=knowledge_nodes, error_nodes=error_nodes)
        if not plan:
            return

        self.store.apply_graph_cleanup_plan(
            day,
            knowledge_merges=plan.get("knowledge_merges") or [],
            error_merges=plan.get("error_merges") or [],
            error_refinements=plan.get("error_refinements") or [],
        )
        self._last_graph_cleanup_at = time.monotonic()

    async def _extract_graph_cleanup_plan(
        self,
        *,
        knowledge_nodes: list[dict[str, Any]],
        error_nodes: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        prompt = "\n\n".join([
            "Review these graph nodes for obvious duplicates.",
            "Only merge labels that clearly mean the same learning point or the same error pattern.",
            "Do not merge parent-child concepts.",
            "Prefer merging candidate nodes into active nodes when possible.",
            "For error nodes, you may refine an overly specific label into a shorter reusable pattern label.",
            "For each error refinement, provide one short classic_example and a brief note if useful.",
            "If an error node lacks classic_example or uses a too-specific label, emit an error_refinement even when no merge is needed.",
            "Return empty arrays if no merge is needed.",
            "Knowledge nodes:",
            json.dumps(knowledge_nodes, ensure_ascii=False, indent=2),
            "Error nodes:",
            json.dumps(error_nodes, ensure_ascii=False, indent=2),
        ])

        raw_payload: dict[str, Any] | None = None
        forced = {"type": "function", "function": {"name": "save_graph_cleanup_plan"}}
        try:
            response: "LLMResponse" = await self.provider.chat_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You clean graph labels for a middle/high-school math tutor. "
                            "Only output obvious duplicate merges and concise reusable error-pattern refinements. "
                            "When specific or under-described error nodes are present, do not leave error_refinements empty."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                tools=_GRAPH_CLEANUP_TOOL,
                model=self.model,
                tool_choice=forced,
            )
            if response.finish_reason == "error" and _is_tool_choice_unsupported(response.content):
                response = await self.provider.chat_with_retry(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You clean graph labels for a middle/high-school math tutor. "
                                "Return concise JSON with knowledge_merges, error_merges, and error_refinements. "
                                "When specific or under-described error nodes are present, do not leave error_refinements empty."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    tools=_GRAPH_CLEANUP_TOOL,
                    model=self.model,
                    tool_choice="auto",
                )
            if response.has_tool_calls:
                raw_payload = _normalize_tool_args(response.tool_calls[0].arguments)
            if raw_payload is None:
                raw_payload = _extract_json_object(response.content)
        except Exception:
            logger.exception("Graph cleanup extraction failed")
            return None

        if not isinstance(raw_payload, dict):
            return None
        return {
            "knowledge_merges": raw_payload.get("knowledge_merges") or [],
            "error_merges": raw_payload.get("error_merges") or [],
            "error_refinements": raw_payload.get("error_refinements") or [],
        }

    async def _maybe_refresh_daily(self, day: date) -> None:
        if not self._should_refresh(
            day,
            self._last_daily_refresh,
            interval_s=self._DAILY_REFRESH_INTERVAL_S,
            required_path=self.store._day_paths(day)[1],
        ):
            return
        lock = self._daily_locks.setdefault(day, asyncio.Lock())
        async with lock:
            if not self._should_refresh(
                day,
                self._last_daily_refresh,
                interval_s=self._DAILY_REFRESH_INTERVAL_S,
                required_path=self.store._day_paths(day)[1],
            ):
                return
            await self.store.ensure_daily_summary(day, self.provider, self.model, sessions=self.sessions)
            self._last_daily_refresh[day] = time.monotonic()

    async def _maybe_refresh_weekly(self, day: date) -> None:
        stem = _week_file_stem(day)
        weekly_path = self.store.weekly_memory_dir / stem / f"{stem}.md"
        if not self._should_refresh(
            day,
            self._last_weekly_refresh,
            interval_s=self._WEEKLY_REFRESH_INTERVAL_S,
            required_path=weekly_path,
        ):
            return
        lock = self._weekly_locks.setdefault(day, asyncio.Lock())
        async with lock:
            if not self._should_refresh(
                day,
                self._last_weekly_refresh,
                interval_s=self._WEEKLY_REFRESH_INTERVAL_S,
                required_path=weekly_path,
            ):
                return
            await self.store.ensure_weekly_summary(day, self.provider, self.model)
            self._last_weekly_refresh[day] = time.monotonic()

    @staticmethod
    def _should_refresh(
        day: date,
        stamps: dict[date, float],
        *,
        interval_s: int,
        required_path: Path,
    ) -> bool:
        if not required_path.exists():
            return True
        last = stamps.get(day)
        if last is None:
            return True
        return (time.monotonic() - last) >= interval_s

    def _today(self) -> date:
        return datetime.now(self.timezone).date()
