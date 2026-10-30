"""Action dispatchers routing processed intelligence to target destinations."""

from .router import ActionRouter
from .obsidian import ObsidianDispatcher
from .email_dispatcher import EmailDispatcher
from .slides import SlidesDispatcher
from .calendar import CalendarDispatcher

__all__ = [
    "ActionRouter",
    "ObsidianDispatcher",
    "EmailDispatcher",
    "SlidesDispatcher",
    "CalendarDispatcher",
]
