"""Message bus module for decoupled channel-agent communication."""

from .events import InboundMessage, OutboundMessage
from .queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
