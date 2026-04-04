"""Format attachment-based math replies into stable themed sections."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..providers.base import LLMProvider

_SECTION_SYSTEM_PROMPT = """你是 MathClaw 的附件题目整理器，也是一个擅长把数学题反馈写得清晰、好看、鼓励人的学习教练。

你会收到：
1. 用户问题
2. 附件解析后的题面/材料
3. 主回答草稿
4. 知识点图谱和错题图谱的相关节点

你的任务是把最终回复严格整理成 3 个主题块，且只输出下面这 3 个 XML 标签，不要输出其它说明：
<grading>...</grading>
<guidance>...</guidance>
<variations>...</variations>

要求：
- grading：写“批改情况”。优先判断对错、失分点、看不清的地方、需要订正的地方。看不全就明确说哪些能判断，哪些暂时不能判断。
- guidance：写“引导讲解”。面向初高中学生，分步骤讲清楚，不只报答案，要解释为什么。
- variations：写“变式题”。必须结合给定的知识点图谱和错题图谱，给出 2 到 3 道变式题。每道变式题都要包含：题目、对应知识点、易错提醒。
- 风格要比普通说明更有吸引力，但不要花哨过头。允许适量使用 emoji、项目符号、编号、简短表格。
- grading 里尽量包含：
  1. 一句总体评价
  2. 一个小的“批改总览”表格或清单
  3. 1 到 2 条订正建议
- guidance 里尽量包含：
  1. “先看结论”一句
  2. 2 到 5 个分步骤讲解
  3. 一个“易错提醒”
  4. 一句简短鼓励
- variations 里尽量包含：
  1. 一个“为什么练这些题”的开场
  2. 2 到 3 道分层变式题
  3. 每道题都用清晰的小结构：题目 / 对应知识点 / 易错提醒
- 语言自然、教学化、带一点温度，不要机械。
- 不要重复 XML 标签名之外的标题，不要加 Markdown 代码块。
"""


@dataclass(slots=True)
class AttachmentReplySections:
    grading: str
    guidance: str
    variations: str

    def as_markdown(self) -> str:
        parts = [
            f"📝 批改情况\n\n{self._clean_section(self.grading, ('批改情况', '总体评价'))}",
            f"💡 引导讲解\n\n{self._clean_section(self.guidance, ('引导讲解', '先看结论'))}",
            f"🧩 变式题\n\n{self._clean_section(self.variations, ('变式题', '为什么练这些题'))}",
        ]
        return "\n\n".join(part for part in parts if part.strip())

    def as_wecom_messages(self, notice: str | None = None) -> list[str]:
        grading = self._clean_section(self.grading, ("批改情况", "总体评价"))
        if notice:
            grading = f"{notice}\n\n{grading}"
        return [
            f"📝 批改情况\n\n{grading}",
            f"💡 引导讲解\n\n{self._clean_section(self.guidance, ('引导讲解', '先看结论'))}",
            f"🧩 变式题\n\n{self._clean_section(self.variations, ('变式题', '为什么练这些题'))}",
        ]

    @staticmethod
    def _clean_section(text: str, heading_keywords: tuple[str, ...]) -> str:
        cleaned = text.strip()
        for _ in range(2):
            lines = cleaned.splitlines()
            if not lines:
                return ""
            first = lines[0].strip().lstrip("#").strip()
            normalized = re.sub(r"^[^\w\u4e00-\u9fff]+", "", first)
            if any(keyword in normalized for keyword in heading_keywords):
                cleaned = "\n".join(lines[1:]).strip()
                continue
            break
        return cleaned


class AttachmentReplyFormatter:
    """Create stable three-part replies for attachment-based math turns."""

    def __init__(self, workspace: Path, provider: LLMProvider, model: str):
        self.workspace = workspace
        self.provider = provider
        self.model = model

    async def format(
        self,
        *,
        question: str,
        attachment_context: str,
        raw_answer: str,
    ) -> AttachmentReplySections | None:
        prompt = self._build_prompt(
            question=question,
            attachment_context=attachment_context,
            raw_answer=raw_answer,
        )
        response = await self.provider.chat(
            messages=[
                {"role": "system", "content": _SECTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            model=self.model,
            max_tokens=min(getattr(self.provider.generation, "max_tokens", 4096), 2600),
            temperature=0.4,
            reasoning_effort=getattr(self.provider.generation, "reasoning_effort", None),
        )
        return self._parse_sections(response.content or "")

    def _build_prompt(self, *, question: str, attachment_context: str, raw_answer: str) -> str:
        query = "\n".join(part for part in [question, attachment_context, raw_answer] if part).strip()
        knowledge_context = self._render_graph_matches(
            self.workspace / "memory" / "graphs" / "knowledge_graph.json",
            query=query,
            graph_name="知识点图谱",
            label_key="label",
            weight_keys=("risk", "importance"),
            extra_keys=("mastery", "notes"),
        )
        error_context = self._render_graph_matches(
            self.workspace / "memory" / "graphs" / "error_graph.json",
            query=query,
            graph_name="错题图谱",
            label_key="label",
            weight_keys=("severity",),
            extra_keys=("notes",),
        )
        return (
            f"用户问题：\n{self._clip(question, 1200)}\n\n"
            f"附件解析内容：\n{self._clip(attachment_context, 5000)}\n\n"
            f"主回答草稿：\n{self._clip(raw_answer, 5000)}\n\n"
            f"{knowledge_context}\n\n"
            f"{error_context}"
        )

    def _render_graph_matches(
        self,
        path: Path,
        *,
        query: str,
        graph_name: str,
        label_key: str,
        weight_keys: tuple[str, ...],
        extra_keys: tuple[str, ...],
    ) -> str:
        data = self._load_json(path)
        nodes = data.get("nodes", []) if isinstance(data, dict) else []
        if not isinstance(nodes, list) or not nodes:
            return f"{graph_name}：暂无可用节点。"

        ranked = sorted(
            nodes,
            key=lambda node: self._score_node(node, query, label_key, weight_keys),
            reverse=True,
        )[:3]
        lines = [f"{graph_name}相关节点："]
        for node in ranked:
            label = str(node.get(label_key, "")).strip() or "未命名节点"
            attrs: list[str] = []
            for key in weight_keys + extra_keys:
                value = node.get(key)
                if value in (None, "", [], {}):
                    continue
                attrs.append(f"{key}={value}")
            examples = self._recent_examples(node.get("examples"))
            related_points = node.get("related_knowledge_points")
            if related_points:
                attrs.append(f"related={','.join(str(item) for item in related_points[:3])}")
            if examples:
                attrs.append(f"examples={examples}")
            line = f"- {label}"
            if attrs:
                line += f" ({'; '.join(attrs)})"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _recent_examples(value: Any) -> str:
        if not isinstance(value, list):
            return ""
        samples: list[str] = []
        for item in value[:2]:
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
            else:
                text = str(item).strip()
            if text:
                samples.append(text)
        return " | ".join(samples)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _score_node(
        self,
        node: dict[str, Any],
        query: str,
        label_key: str,
        weight_keys: tuple[str, ...],
    ) -> float:
        haystack = self._node_text(node, label_key).lower()
        score = 0.0
        for term in self._extract_terms(query):
            if term in haystack:
                score += 4.0 if len(term) >= 4 else 2.0
        for key in weight_keys:
            value = node.get(key)
            if isinstance(value, (int, float)):
                score += float(value)
        return score

    @staticmethod
    def _node_text(node: dict[str, Any], label_key: str) -> str:
        parts: list[str] = [str(node.get(label_key, ""))]
        for key in ("notes", "label", "type"):
            value = node.get(key)
            if value:
                parts.append(str(value))
        for key in ("related_knowledge_points", "correction_suggestions"):
            value = node.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value[:5])
        examples = node.get("examples")
        if isinstance(examples, list):
            for item in examples[:3]:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                elif item:
                    parts.append(str(item))
        return "\n".join(parts)

    @staticmethod
    def _extract_terms(text: str) -> list[str]:
        lowered = text.lower()
        terms = re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", lowered)
        seen: set[str] = set()
        ordered: list[str] = []
        for term in terms:
            if term in seen:
                continue
            seen.add(term)
            ordered.append(term)
        return ordered[:24]

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit] + "\n...(truncated)"

    @staticmethod
    def _extract_tag(content: str, tag: str) -> str:
        match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", content, flags=re.S)
        return match.group(1).strip() if match else ""

    @classmethod
    def _parse_sections(cls, content: str) -> AttachmentReplySections | None:
        grading = cls._extract_tag(content, "grading")
        guidance = cls._extract_tag(content, "guidance")
        variations = cls._extract_tag(content, "variations")
        if not grading or not guidance or not variations:
            return None
        return AttachmentReplySections(
            grading=grading,
            guidance=guidance,
            variations=variations,
        )
