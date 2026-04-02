"""Tests for the structured learning-memory store."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from nanobot.agent.memory import MemoryStore


def _make_messages(day: str) -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": "今天做了函数单调性和奇偶性的题，单调区间总是写错。",
            "timestamp": f"{day}T09:00:00",
        },
        {
            "role": "assistant",
            "content": "主要问题是符号方向和区间判断，建议先回顾导数与定义域。",
            "timestamp": f"{day}T09:05:00",
        },
    ]


def _make_response(
    *,
    content: str | None = None,
    finish_reason: str = "stop",
    tool_payload: object | None = None,
) -> SimpleNamespace:
    tool_calls = []
    if tool_payload is not None:
        tool_calls.append(SimpleNamespace(arguments=tool_payload))
    return SimpleNamespace(
        content=content,
        finish_reason=finish_reason,
        tool_calls=tool_calls,
        has_tool_calls=bool(tool_calls),
    )


def _daily_payload(day: str, *, label: str = "函数单调性") -> dict[str, object]:
    return {
        "date": day,
        "learning_status_summary": "今天主要暴露出函数性质判断不稳定，解题速度一般，错因集中。",
        "tomorrow_study_suggestions": [
            "先复盘函数单调性的判定步骤。",
            "把奇偶性和定义域联动做一轮专项练习。",
        ],
        "high_risk_knowledge_points": [
            {
                "label": label,
                "risk": 0.86,
                "mastery": 0.34,
                "importance": 0.9,
                "notes": "遇到含参数区间时容易漏条件。",
                "examples": ["求导后忘记检查定义域。"],
                "prerequisites": ["导数符号"],
                "similar_points": ["函数奇偶性"],
                "contains_points": ["单调区间"],
                "related_points": ["定义域约束"],
            }
        ],
        "high_frequency_error_types": [
            {
                "label": "符号方向反了",
                "severity": 0.82,
                "repeated": True,
                "notes": "不等号翻转经常遗漏。",
                "examples": ["由 f'(x) > 0 推区间时写反。"],
                "related_knowledge_points": [label],
                "similar_errors": ["区间端点漏写"],
                "correction_suggestions": ["先列符号表，再写结论。"],
            }
        ],
    }


class WeeklyAwareProvider:
    def __init__(self, weekly_markdown: str):
        self.weekly_markdown = weekly_markdown
        self.calls: list[dict[str, object]] = []

    async def chat_with_retry(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("tools"):
            prompt = str(kwargs["messages"][-1]["content"])
            match = re.search(r"for (\d{4}-\d{2}-\d{2})", prompt)
            day = match.group(1) if match else "2026-03-29"
            return _make_response(tool_payload=_daily_payload(day, label=f"知识点-{day[-2:]}"))
        return _make_response(content=self.weekly_markdown)


class TestStructuredLearningMemory:
    @pytest.mark.asyncio
    async def test_consolidate_writes_daily_files_and_graphs(self, tmp_path: Path) -> None:
        store = MemoryStore(tmp_path)
        provider = AsyncMock()
        provider.chat_with_retry = AsyncMock(return_value=_make_response(tool_payload=_daily_payload("2026-03-29")))

        result = await store.consolidate(
            _make_messages("2026-03-29"),
            provider,
            "test-model",
            session_key="cli:test",
        )

        assert result is True

        day_root = tmp_path / "memory" / "daily_memory" / "2026.3.29"
        markdown_file = day_root / "2026_3_29.md"
        json_file = day_root / "2026_3_29.json"
        events_file = day_root / "events.jsonl"

        assert markdown_file.exists()
        assert json_file.exists()
        assert events_file.exists()

        payload = json.loads(json_file.read_text(encoding="utf-8"))
        assert payload["date"] == "2026-03-29"
        assert payload["high_risk_knowledge_points"][0]["label"] == "函数单调性"
        assert payload["high_frequency_error_types"][0]["label"] == "符号方向反了"

        event_rows = [json.loads(line) for line in events_file.read_text(encoding="utf-8").splitlines()]
        assert len(event_rows) == 2
        assert event_rows[0]["session_key"] == "cli:test"

        knowledge_graph = json.loads(store.knowledge_graph_file.read_text(encoding="utf-8"))
        assert any(node["label"] == "函数单调性" for node in knowledge_graph["nodes"])
        assert any(edge["relation"] == "prerequisite" for edge in knowledge_graph["edges"])

        error_graph = json.loads(store.error_graph_file.read_text(encoding="utf-8"))
        error_node = next(node for node in error_graph["nodes"] if node["label"] == "符号方向反了")
        assert error_node["related_knowledge_points"] == ["函数单调性"]
        assert any(edge["relation"] == "corresponds_to" for edge in error_graph["edges"])

        assert store.memory_file.exists()
        assert "Learning Memory Snapshot" in store.memory_file.read_text(encoding="utf-8")
        assert "archived 2 messages" in store.history_file.read_text(encoding="utf-8")

        _, kwargs = provider.chat_with_retry.await_args
        assert kwargs["model"] == "test-model"
        assert kwargs["tools"]
        assert kwargs["tool_choice"]["function"]["name"] == "save_learning_memory"

    @pytest.mark.asyncio
    async def test_consolidate_falls_back_to_local_summary_without_tool_call(self, tmp_path: Path) -> None:
        store = MemoryStore(tmp_path)
        provider = AsyncMock()
        provider.chat_with_retry = AsyncMock(return_value=_make_response(content="Plain text only."))

        result = await store.consolidate(_make_messages("2026-03-29"), provider, "test-model")

        assert result is True
        payload = json.loads(
            (tmp_path / "memory" / "daily_memory" / "2026.3.29" / "2026_3_29.json").read_text(encoding="utf-8")
        )
        assert payload["high_risk_knowledge_points"] == []
        assert payload["high_frequency_error_types"] == []
        assert payload["learning_status_summary"]
        assert payload["tomorrow_study_suggestions"]

    @pytest.mark.asyncio
    async def test_tool_choice_fallback_retries_with_auto(self, tmp_path: Path) -> None:
        store = MemoryStore(tmp_path)
        error_response = _make_response(
            content='The tool_choice parameter should be ["none", "auto"]',
            finish_reason="error",
        )
        ok_response = _make_response(tool_payload=_daily_payload("2026-03-29"))
        call_log: list[dict[str, object]] = []

        async def _chat(**kwargs):
            call_log.append(kwargs)
            return error_response if len(call_log) == 1 else ok_response

        provider = AsyncMock()
        provider.chat_with_retry = AsyncMock(side_effect=_chat)

        result = await store.consolidate(_make_messages("2026-03-29"), provider, "test-model")

        assert result is True
        assert len(call_log) == 2
        assert isinstance(call_log[0]["tool_choice"], dict)
        assert call_log[1]["tool_choice"] == "auto"
        assert (tmp_path / "memory" / "daily_memory" / "2026.3.29" / "2026_3_29.json").exists()

    @pytest.mark.asyncio
    async def test_seven_days_generate_weekly_plan(self, tmp_path: Path) -> None:
        weekly_markdown = "# 下周学习计划\n\n- 周一到周三复盘高风险知识点。\n- 周四到周五刷错题变式。\n"
        provider = WeeklyAwareProvider(weekly_markdown)
        store = MemoryStore(tmp_path)
        start = date(2026, 3, 25)

        for offset in range(7):
            current = start + timedelta(days=offset)
            await store.consolidate(
                _make_messages(current.isoformat()),
                provider,
                "test-model",
                session_key="cron:daily",
            )

        weekly_file = (
            tmp_path
            / "memory"
            / "weekly_memory"
            / "2026_3_25_to_2026_3_31"
            / "2026_3_25_to_2026_3_31.md"
        )
        assert weekly_file.exists()
        assert weekly_file.read_text(encoding="utf-8") == weekly_markdown
        assert len(provider.calls) == 8

    def test_low_signal_knowledge_nodes_are_archived_when_stale(self, tmp_path: Path) -> None:
        store = MemoryStore(tmp_path)
        old_day = date(2026, 1, 1)
        store._update_knowledge_graph(old_day, [
            {
                "label": "旧知识点",
                "risk": 0.2,
                "mastery": 0.8,
                "importance": 0.2,
                "notes": "",
                "last_seen": old_day.isoformat(),
                "examples": [],
                "prerequisites": [],
                "similar_points": [],
                "contains_points": [],
                "related_points": [],
            }
        ])

        store._update_knowledge_graph(old_day + timedelta(days=50), [])

        graph = json.loads(store.knowledge_graph_file.read_text(encoding="utf-8"))
        assert graph["nodes"] == []
        assert any(node["label"] == "旧知识点" for node in graph["archived_nodes"])
