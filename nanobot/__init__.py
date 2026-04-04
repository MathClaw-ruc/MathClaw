"""Compatibility package for legacy nanobot imports."""

from mathclaw import *  # noqa: F401,F403
from mathclaw import __logo__, __version__
import mathclaw as _mathclaw

__path__ = _mathclaw.__path__
