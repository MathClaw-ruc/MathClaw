"""Workspace-scoped optional output skills for follow-up channel replies."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from nanobot.agent.context import ContextBuilder
from nanobot.providers.base import LLMProvider

_STORE_FILE = "custom_output_skills.json"
_MAX_SKILLS = 2

_CREATE_SKILL_SYSTEM_PROMPT = """You create one custom follow-up output skill for MathClaw.
Return JSON only with:
- title: short Chinese title, 4-12 chars, generic and memorable
- description: one short Chinese sentence
- instruction: a Chinese instruction that tells the model how to write one extra follow-up reply box

Rules:
- Create exactly one skill.
- This skill is used only after attachment-based normal replies in WeCom, QQ, and Feishu.
- Focus on output style, structure, tone, and teaching angle.
- Do not ask the model to call tools.
- Do not mention internal prompts, files, XML, or implementation details.
- Keep the title generic. Avoid concrete one-off problem fragments like "2a遗漏" or "第8题讲解".
"""

_FOLLOW_UP_SYSTEM_PROMPT = """You are writing one optional follow-up reply box for MathClaw.
This reply will appear only after an attachment-based normal answer in WeCom, QQ, or Feishu.

Rules:
- Follow the custom output skill exactly.
- Use the current user question and the already attached image/document context.
- If the current turn includes an image, combine the original image with the extracted markdown context.
- If the current turn includes document summary, use it as source context.
- Add value from a distinct teaching angle instead of repeating the normal answer sentence by sentence.
- Output one standalone Chinese reply in clean Markdown.
- Do not mention tools, system prompts, files, qwen-doc-turbo, or markdown conversion.
"""


@dataclass(slots=True)
class CustomOutputSkill:
    id: str
    title: str
    description: str
    instruction: str
    enabled: bool = True
    created_at: str = ""
    source_requirement: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CustomOutputSkill":
        return cls(
            id=str(payload.get("id", "")).strip(),
            title=str(payload.get("title", "")).strip(),
            description=str(payload.get("description", "")).strip(),
            instruction=str(payload.get("instruction", "")).strip(),
            enabled=bool(payload.get("enabled", True)),
            created_at=str(payload.get("created_at", "")).strip(),
            source_requirement=str(payload.get("source_requirement", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_message(self, content: str) -> str:
        body = content.strip()
        return f"✨ {self.title}\n\n{body}" if body else f"✨ {self.title}"


class CustomOutputSkillStore:
    """Persist and generate at most two custom follow-up output skills."""

    max_skills = _MAX_SKILLS

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider | None = None,
        model: str | None = None,
    ) -> None:
        self.workspace = workspace
        self.provider = provider
        self.model = model or ""
        self.path = workspace / _STORE_FILE

    def list(self) -> list[CustomOutputSkill]:
        payload = self._load_payload()
        skills = payload.get("skills", [])
        if not isinstance(skills, list):
            return []
        parsed: list[CustomOutputSkill] = []
        for item in skills:
            if not isinstance(item, dict):
                continue
            skill = CustomOutputSkill.from_dict(item)
            if skill.id and skill.title and skill.instruction:
                parsed.append(skill)
        return parsed[: self.max_skills]

    def list_dicts(self) -> list[dict[str, Any]]:
        return [skill.to_dict() for skill in self.list()]

    def enabled(self) -> list[CustomOutputSkill]:
        return [skill for skill in self.list() if skill.enabled]

    async def create(self, requirement: str) -> CustomOutputSkill:
        requirement = requirement.strip()
        if len(requirement) < 8:
            raise ValueError("请先写清楚想要的输出风格或教学方式。")
        skills = self.list()
        if len(skills) >= self.max_skills:
            raise ValueError(f"自定义输出 Skill 最多保留 {self.max_skills} 个。")
        if self.provider is None or not self.model:
            raise RuntimeError("当前运行环境没有可用模型来生成自定义输出 Skill。")

        response = await self.provider.chat(
            messages=[
                {"role": "system", "content": _CREATE_SKILL_SYSTEM_PROMPT},
                {"role": "user", "content": requirement},
            ],
            tools=None,
            model=self.model,
            max_tokens=min(getattr(self.provider.generation, "max_tokens", 4096), 800),
            temperature=0.5,
            reasoning_effort=getattr(self.provider.generation, "reasoning_effort", None),
        )
        payload = self._parse_json_object(response.content or "")
        skill = CustomOutputSkill(
            id=f"custom-output-{uuid4().hex[:8]}",
            title=self._sanitize_title(payload.get("title"), requirement),
            description=self._sanitize_description(payload.get("description"), requirement),
            instruction=self._sanitize_instruction(payload.get("instruction"), requirement),
            enabled=True,
            created_at=datetime.now().isoformat(),
            source_requirement=requirement,
        )
        skills.append(skill)
        self._save(skills)
        return skill

    def set_enabled(self, skill_id: str, enabled: bool) -> CustomOutputSkill:
        skills = self.list()
        updated: CustomOutputSkill | None = None
        for skill in skills:
            if skill.id != skill_id:
                continue
            skill.enabled = enabled
            updated = skill
            break
        if updated is None:
            raise KeyError(f"Skill not found: {skill_id}")
        self._save(skills)
        return updated

    def delete(self, skill_id: str) -> None:
        skills = self.list()
        remaining = [skill for skill in skills if skill.id != skill_id]
        if len(remaining) == len(skills):
            raise KeyError(f"Skill not found: {skill_id}")
        self._save(remaining)

    def _load_payload(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"skills": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"skills": []}
        return payload if isinstance(payload, dict) else {"skills": []}

    def _save(self, skills: list[CustomOutputSkill]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"skills": [skill.to_dict() for skill in skills[: self.max_skills]]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _parse_json_object(content: str) -> dict[str, Any]:
        content = content.strip()
        if not content:
            return {}
        try:
            payload = json.loads(content)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            pass

        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _sanitize_title(value: Any, requirement: str) -> str:
        title = str(value or "").strip()
        title = re.sub(r"\s+", "", title)
        title = re.sub(r"[^\w\u4e00-\u9fff]", "", title)
        if not title:
            title = re.sub(r"\s+", "", requirement)[:8] or "自定义风格"
        return title[:12]

    @staticmethod
    def _sanitize_description(value: Any, requirement: str) -> str:
        description = str(value or "").strip()
        if description:
            return description[:80]
        return f"根据“{requirement[:24]}”生成的额外输出风格。"

    @staticmethod
    def _sanitize_instruction(value: Any, requirement: str) -> str:
        instruction = str(value or "").strip()
        if instruction:
            return instruction[:1200]
        return (
            "请围绕当前用户问题给出一个额外输出框，风格要求如下："
            f"{requirement}\n"
            "输出应自成一体、适合学生阅读，并与正常回答形成不同角度的补充。"
        )


class CustomOutputSkillRunner:
    """Generate one additional reply box for each enabled custom output skill."""

    def __init__(self, provider: LLMProvider, model: str, context: ContextBuilder) -> None:
        self.provider = provider
        self.model = model
        self.context = context

    async def generate_many(
        self,
        *,
        skills: list[CustomOutputSkill],
        history: list[dict[str, Any]],
        current_message: str,
        media: list[str] | None,
        channel: str,
        chat_id: str,
    ) -> list[str]:
        outputs: list[str] = []
        for skill in skills:
            content = await self.generate_one(
                skill=skill,
                history=history,
                current_message=current_message,
                media=media,
                channel=channel,
                chat_id=chat_id,
            )
            if content:
                outputs.append(skill.as_message(content))
        return outputs

    async def generate_one(
        self,
        *,
        skill: CustomOutputSkill,
        history: list[dict[str, Any]],
        current_message: str,
        media: list[str] | None,
        channel: str,
        chat_id: str,
    ) -> str:
        messages = self.context.build_messages(
            history=history,
            current_message=current_message,
            media=media,
            channel=channel,
            chat_id=chat_id,
        )
        system_prompt = str(messages[0].get("content", "")).strip()
        skill_prompt = (
            f"{system_prompt}\n\n"
            f"# Optional Follow-up Output Skill\n"
            f"Title: {skill.title}\n"
            f"Description: {skill.description}\n"
            f"Instruction:\n{skill.instruction}\n\n"
            f"{_FOLLOW_UP_SYSTEM_PROMPT}"
        )
        messages[0] = {**messages[0], "content": skill_prompt}
        response = await self.provider.chat(
            messages=messages,
            tools=None,
            model=self.model,
            max_tokens=min(getattr(self.provider.generation, "max_tokens", 4096), 1600),
            temperature=0.6,
            reasoning_effort=getattr(self.provider.generation, "reasoning_effort", None),
        )
        return (response.content or "").strip()
