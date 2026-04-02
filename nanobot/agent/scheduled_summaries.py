"""Scheduled daily and weekly summary delivery for MathClaw."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from loguru import logger

from nanobot.agent.memory import MemoryStore
from nanobot.bus.events import OutboundMessage

if TYPE_CHECKING:
    from nanobot.bus.queue import MessageBus
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronJob
    from nanobot.providers.base import LLMProvider
    from nanobot.session.manager import SessionManager


_DAILY_SUMMARY_MARKER = "__mathclaw_daily_summary__"
_WEEKLY_SUMMARY_MARKER = "__mathclaw_weekly_summary__"
_SKIP_CHANNELS = {"cli", "system"}
_BUSLESS_CHANNELS = {"cli", "system", "web"}


class ScheduledSummaryManager:
    """Generate one summary per period and broadcast it to all active channels."""

    def __init__(
        self,
        *,
        workspace: Path,
        provider: "LLMProvider",
        model: str,
        sessions: "SessionManager",
        bus: "MessageBus",
        timezone: str | None = None,
    ) -> None:
        self.store = MemoryStore(workspace)
        self.provider = provider
        self.model = model
        self.sessions = sessions
        self.bus = bus
        self.timezone = ZoneInfo(timezone or "Asia/Shanghai")

    def ensure_jobs(self, cron: "CronService") -> None:
        self._ensure_job(
            cron=cron,
            marker=_DAILY_SUMMARY_MARKER,
            name="MathClaw Daily Summary",
            expr="0 22 * * *",
        )
        self._ensure_job(
            cron=cron,
            marker=_WEEKLY_SUMMARY_MARKER,
            name="MathClaw Weekly Summary",
            expr="10 22 * * 5",
        )

    async def handle_job(self, job: "CronJob") -> str | None:
        marker = (job.payload.message or "").strip()
        if marker == _DAILY_SUMMARY_MARKER:
            return await self.run_daily_summary()
        if marker == _WEEKLY_SUMMARY_MARKER:
            return await self.run_weekly_summary()
        return None

    async def run_daily_summary(self, target_day: date | None = None) -> str | None:
        day = target_day or self._today()
        markdown = await self.store.ensure_daily_summary(
            day,
            self.provider,
            self.model,
            sessions=self.sessions,
        )
        if not markdown:
            logger.info("Daily summary skipped for {}: no conversations", day.isoformat())
            return None

        targets = self._active_targets(day, day)
        if not targets:
            logger.info("Daily summary generated for {} but no active channels were found", day.isoformat())
            return markdown

        await self._broadcast(markdown, targets, summary_type="daily")
        return markdown

    async def run_weekly_summary(self, target_day: date | None = None) -> str | None:
        day = target_day or self._today()
        await self.store.ensure_daily_summary(
            day,
            self.provider,
            self.model,
            sessions=self.sessions,
        )
        markdown = await self.store.ensure_weekly_summary(day, self.provider, self.model)
        if not markdown:
            logger.info("Weekly summary skipped for {}: no daily summaries available", day.isoformat())
            return None

        start_day = day - timedelta(days=6)
        targets = self._active_targets(start_day, day)
        if not targets:
            logger.info(
                "Weekly summary generated for {} to {} but no active channels were found",
                start_day.isoformat(),
                day.isoformat(),
            )
            return markdown

        await self._broadcast(markdown, targets, summary_type="weekly")
        return markdown

    def _ensure_job(
        self,
        *,
        cron: "CronService",
        marker: str,
        name: str,
        expr: str,
    ) -> None:
        from nanobot.cron.types import CronSchedule

        for job in cron.list_jobs(include_disabled=True):
            if (job.payload.message or "").strip() != marker:
                continue
            if (
                job.schedule.kind == "cron"
                and job.schedule.expr == expr
                and job.schedule.tz == self.timezone.key
            ):
                if not job.enabled:
                    cron.enable_job(job.id, True)
                return
            cron.remove_job(job.id)

        cron.add_job(
            name=name,
            schedule=CronSchedule(kind="cron", expr=expr, tz=self.timezone.key),
            message=marker,
            deliver=False,
        )

    def _today(self) -> date:
        return datetime.now(self.timezone).date()

    def _active_targets(self, start_day: date, end_day: date) -> list[tuple[str, str]]:
        targets: dict[str, tuple[str, str]] = {}
        for item in self.sessions.list_sessions():
            session_key = str(item.get("key") or "").strip()
            if ":" not in session_key:
                continue
            channel, chat_id = session_key.split(":", 1)
            if channel in _SKIP_CHANNELS or not chat_id:
                continue

            session = self.sessions.get_or_create(session_key)
            if any(self._message_in_range(message, start_day, end_day) for message in session.messages):
                targets[session_key] = (channel, chat_id)
        return list(targets.values())

    @staticmethod
    def _message_in_range(message: dict, start_day: date, end_day: date) -> bool:
        if message.get("summary_push"):
            return False
        if message.get("role") not in {"user", "assistant"}:
            return False
        observed_at = message.get("timestamp")
        if not observed_at:
            return False
        try:
            current_day = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00")).date()
        except ValueError:
            return False
        return start_day <= current_day <= end_day

    async def _broadcast(
        self,
        content: str,
        targets: list[tuple[str, str]],
        *,
        summary_type: str,
    ) -> None:
        for channel, chat_id in targets:
            session = self.sessions.get_or_create(f"{channel}:{chat_id}")
            session.add_message("assistant", content, summary_push=True, summary_type=summary_type)
            self.sessions.save(session)

            if channel in _BUSLESS_CHANNELS:
                continue

            await self.bus.publish_outbound(
                OutboundMessage(
                    channel=channel,
                    chat_id=chat_id,
                    content=content,
                    metadata={"summary_push": True, "summary_type": summary_type},
                )
            )
