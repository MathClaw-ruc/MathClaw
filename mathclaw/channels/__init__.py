"""Chat channels module with plugin architecture."""

from .base import BaseChannel
from .manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
