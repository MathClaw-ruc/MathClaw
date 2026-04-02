"""Shared attachment rules for chat and channel inputs."""

from __future__ import annotations

import asyncio
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.providers.base import LLMProvider
from nanobot.providers.openai_compat_provider import OpenAICompatProvider

_PENDING_ATTACHMENTS_KEY = "_pending_attachments"
_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
}
_DOCUMENT_EXTENSIONS = {
    ".pdf", ".ppt", ".pptx", ".doc", ".docx",
}
_DROP_LINE_PREFIXES = (
    "[image:",
    "[image]",
    "[image: download failed]",
    "[image omitted]",
    "[file:",
    "[file]",
    "[file: download failed]",
    "[video]",
    "[video:",
    "[audio]",
    "[audio:",
    "[Image: source:",
    "[File: source:",
    "[Video: source:",
    "[Audio: source:",
    "[reply to:",
    "[empty message]",
)
_DOC_SUMMARY_SYSTEM_PROMPT = (
    "You prepare document context for MathClaw, a junior and senior high school "
    "math tutor. Read the uploaded file and return a concise answer-oriented summary."
)
_IMAGE_MARKDOWN_PROMPT = (
    "Convert this math-learning image into faithful Markdown for downstream QA.\n"
    "Keep only what is visibly present in the image.\n"
    "Preserve the problem statement, numbered parts, answer choices, tables, axis labels, "
    "diagram labels, and formulas.\n"
    "Write formulas in Markdown/LaTeX when possible.\n"
    "If some text is unclear, mark it as [unclear].\n"
    "Do not solve the problem. Do not add explanations."
)


@dataclass(slots=True)
class PreparedAttachmentTurn:
    """The normalized form of one inbound turn."""

    llm_content: str
    llm_media: list[str]
    session_content: str
    user_text: str = ""
    has_attachments: bool = False
    blocked_reply: str | None = None
    response_notice: str | None = None

    @property
    def should_call_model(self) -> bool:
        return self.blocked_reply is None


@dataclass(slots=True)
class AttachmentBuckets:
    """Classified attachments."""

    images: list[str]
    documents: list[str]
    others: list[str]

    @property
    def all_paths(self) -> list[str]:
        return [*self.images, *self.documents, *self.others]


class AttachmentRules:
    """Apply shared multimodal rules before the main model call."""

    def __init__(self, provider: LLMProvider, final_model: str | None = None):
        self.provider = provider
        self.final_model = final_model or getattr(provider, "default_model", None) or ""

    async def prepare_turn(
        self,
        session: Any,
        content: str,
        media: list[str] | None,
    ) -> PreparedAttachmentTurn:
        """Normalize text + attachments into one LLM-ready turn."""
        current_media = self._dedupe_existing_paths(media or [])
        pending_media = self._get_pending_media(session)
        merged_media = self._dedupe_existing_paths([*pending_media, *current_media])
        buckets = self._classify_media(merged_media)
        user_text = self._extract_user_text(content)

        if buckets.all_paths and not user_text:
            self._set_pending_media(session, merged_media)
            session_content = self._build_session_content("", buckets, waiting=True)
            return PreparedAttachmentTurn(
                llm_content="",
                llm_media=[],
                session_content=session_content,
                user_text="",
                has_attachments=True,
                blocked_reply="已收到附件。请再补充你的文字问题，我会结合附件一起回答。",
            )

        self._clear_pending_media(session)

        llm_content = user_text or content.strip()
        context_sections: list[str] = []
        if buckets.documents:
            summary = await self._summarize_documents(user_text, buckets.documents)
            context_sections.append(self._build_document_context(summary, buckets.documents))

        if buckets.images:
            image_markdown = await self._convert_images_with_markdown_converter(buckets.images)
            context_sections.append(self._build_image_context(image_markdown, buckets.images))

        if context_sections:
            llm_content = self._build_augmented_prompt(user_text, context_sections)

        if buckets.others:
            llm_content = self._append_other_files(llm_content, buckets.others)

        session_content = self._build_session_content(user_text, buckets, waiting=False)
        return PreparedAttachmentTurn(
            llm_content=llm_content,
            llm_media=list(buckets.images),
            session_content=session_content,
            user_text=user_text,
            has_attachments=bool(buckets.all_paths),
            response_notice="已解析图片内容。" if buckets.images else None,
        )

    @staticmethod
    def _dedupe_existing_paths(paths: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for raw in paths:
            if not raw:
                continue
            path = str(Path(raw))
            if path in seen or not Path(path).is_file():
                continue
            seen.add(path)
            ordered.append(path)
        return ordered

    def _get_pending_media(self, session: Any) -> list[str]:
        pending = session.metadata.get(_PENDING_ATTACHMENTS_KEY, [])
        if not isinstance(pending, list):
            return []
        return self._dedupe_existing_paths([str(item) for item in pending])

    @staticmethod
    def _set_pending_media(session: Any, media: list[str]) -> None:
        session.metadata[_PENDING_ATTACHMENTS_KEY] = list(media)

    @staticmethod
    def clear_pending_media(session: Any) -> None:
        session.metadata.pop(_PENDING_ATTACHMENTS_KEY, None)

    def _clear_pending_media(self, session: Any) -> None:
        self.clear_pending_media(session)

    @staticmethod
    def _extract_user_text(content: str) -> str:
        """Drop channel-generated attachment placeholders and keep real text."""
        lines: list[str] = []
        for raw_line in (content or "").splitlines():
            line = raw_line.strip()
            if not line:
                if lines and lines[-1]:
                    lines.append("")
                continue

            lower = line.lower()
            if lower.startswith(_DROP_LINE_PREFIXES):
                continue
            if AttachmentRules._is_legacy_attachment_line(lower):
                continue

            if lower.startswith("[voice]"):
                voice_text = line[7:].strip()
                if voice_text:
                    lines.append(voice_text)
                continue

            if lower.startswith("[transcription:") and line.endswith("]"):
                inner = line[len("[transcription:") : -1].strip()
                if inner:
                    lines.append(inner)
                continue

            lines.append(line)

        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines).strip()

    @staticmethod
    def _is_legacy_attachment_line(lower_line: str) -> bool:
        """Ignore attachment helper text emitted by older channel adapters."""
        return (
            lower_line == "received files:"
            or lower_line.startswith("- ")
            or lower_line.startswith("saved:")
            or lower_line.startswith("saved: [download failed]")
        )

    @staticmethod
    def _classify_media(paths: list[str]) -> AttachmentBuckets:
        images: list[str] = []
        documents: list[str] = []
        others: list[str] = []

        for path in paths:
            suffix = Path(path).suffix.lower()
            mime = mimetypes.guess_type(path)[0] or ""

            if suffix in _DOCUMENT_EXTENSIONS:
                documents.append(path)
            elif suffix in _IMAGE_EXTENSIONS or mime.startswith("image/"):
                images.append(path)
            else:
                others.append(path)

        return AttachmentBuckets(images=images, documents=documents, others=others)

    async def _summarize_documents(self, question: str, document_paths: list[str]) -> str:
        if not question:
            raise RuntimeError("Document summarization requires user text.")

        if not isinstance(self.provider, OpenAICompatProvider):
            raise RuntimeError("Document summarization requires an OpenAI-compatible provider.")

        client = getattr(self.provider, "_client", None)
        if client is None or not hasattr(client, "files"):
            raise RuntimeError("Current provider client does not support file upload.")

        summaries: list[str] = []
        for document_path in document_paths:
            path = Path(document_path)
            file_id = await self._upload_doc_file(client, path)
            try:
                await self._wait_until_processed(client, file_id)
                summary = await self._call_doc_model(question, file_id, path.name)
            finally:
                await self._delete_file(client, file_id)
            summaries.append(f"### {path.name}\n{summary.strip()}")
        return "\n\n".join(summary for summary in summaries if summary.strip())

    async def _upload_doc_file(self, client: Any, path: Path) -> str:
        file_object = await client.files.create(file=path, purpose="file-extract")
        file_id = getattr(file_object, "id", None) or file_object.get("id")
        if not file_id:
            raise RuntimeError(f"Failed to upload document: {path.name}")
        return str(file_id)

    async def _wait_until_processed(self, client: Any, file_id: str) -> None:
        for _ in range(12):
            try:
                file_info = await client.files.retrieve(file_id)
            except Exception:
                return

            status = getattr(file_info, "status", None)
            if status == "processed":
                return
            if status and status not in {"uploaded", "processing"}:
                raise RuntimeError(f"Document parse failed: {status}")
            await asyncio.sleep(1.5)

    async def _call_doc_model(self, question: str, file_id: str, filename: str) -> str:
        prompt = (
            f"用户问题：{question}\n"
            f"请围绕这个问题整理《{filename}》的关键信息。"
            "只保留回答问题直接需要的定义、公式、例题要点、结论或表格信息。"
            "不要输出无关章节，不要重复原文。"
        )
        response = await self.provider.chat(
            messages=[
                {"role": "system", "content": _DOC_SUMMARY_SYSTEM_PROMPT},
                {"role": "system", "content": f"fileid://{file_id}"},
                {"role": "user", "content": prompt},
            ],
            model="qwen-doc-turbo",
            max_tokens=1800,
            temperature=0.1,
        )

        if response.finish_reason == "error" or not (response.content or "").strip():
            raise RuntimeError(f"qwen-doc-turbo failed for {filename}: {response.content or 'empty response'}")
        return response.content or ""

    async def _convert_images_with_markdown_converter(self, image_paths: list[str]) -> str:
        return await asyncio.to_thread(self._run_markdown_converter, image_paths)

    def _run_markdown_converter(self, image_paths: list[str]) -> str:
        if not isinstance(self.provider, OpenAICompatProvider):
            raise RuntimeError("Image Markdown conversion requires an OpenAI-compatible provider.")

        try:
            from markitdown import MarkItDown
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "Image Markdown conversion dependency is missing. Install markitdown first."
            ) from error

        if not self.final_model:
            raise RuntimeError("No final model configured for image Markdown conversion.")

        client = OpenAI(
            api_key=self.provider.api_key or "no-key",
            base_url=self.provider.api_base,
        )
        converter = MarkItDown(
            llm_client=client,
            llm_model=self.final_model,
            llm_prompt=_IMAGE_MARKDOWN_PROMPT,
        )

        parts: list[str] = []
        for image_path in image_paths:
            result = converter.convert(image_path)
            markdown = getattr(result, "text_content", "") or ""
            markdown = markdown.strip()
            if not markdown:
                raise RuntimeError(f"markitdown returned empty content for {Path(image_path).name}")
            parts.append(f"### {Path(image_path).name}\n{markdown}")
        return "\n\n".join(parts)

    async def _delete_file(self, client: Any, file_id: str) -> None:
        try:
            await client.files.delete(file_id)
        except Exception as error:
            logger.debug("AttachmentRules: failed to delete file {}: {}", file_id, error)

    @staticmethod
    def _build_document_context(summary: str, documents: list[str]) -> str:
        names = ", ".join(Path(path).name for path in documents)
        return "\n\n".join(
            part for part in [
                "下面是围绕用户问题整理的文档摘要，请把它当作附件上下文来回答。",
                f"文档：{names}",
                summary,
            ] if part.strip()
        )

    @staticmethod
    def _build_image_context(markdown: str, images: list[str]) -> str:
        names = ", ".join(Path(path).name for path in images)
        return "\n\n".join(
            part for part in [
                "下面是图片经 Markdown Converter 转写后的 Markdown 内容，请把它当作辅助图片上下文来回答。",
                "最终回答时请同时结合原图和下面的转写内容，不要只依赖转写文本。",
                f"图片：{names}",
                markdown,
            ] if part.strip()
        )

    @staticmethod
    def _build_augmented_prompt(question: str, sections: list[str]) -> str:
        parts = [f"用户问题：{question}"] if question else []
        parts.extend(section for section in sections if section.strip())
        return "\n\n".join(parts)

    @staticmethod
    def _append_other_files(content: str, paths: list[str]) -> str:
        names = ", ".join(Path(path).name for path in paths)
        suffix = f"附加文件（未做文档预处理）：{names}"
        return f"{content}\n\n{suffix}" if content else suffix

    @staticmethod
    def _build_session_content(text: str, buckets: AttachmentBuckets, *, waiting: bool) -> str:
        lines: list[str] = []
        if text:
            lines.append(text)
        if buckets.images:
            names = "、".join(Path(path).name for path in buckets.images)
            lines.append(f"[图片：{names}]")
        if buckets.documents:
            names = "、".join(Path(path).name for path in buckets.documents)
            prefix = "已接收文档" if waiting and not text else "文档"
            lines.append(f"[{prefix}：{names}]")
        if buckets.others:
            names = "、".join(Path(path).name for path in buckets.others)
            lines.append(f"[附件：{names}]")
        if waiting and not lines:
            timestamp = datetime.now().strftime("%H:%M")
            lines.append(f"[等待补充问题 {timestamp}]")
        return "\n".join(lines).strip()
