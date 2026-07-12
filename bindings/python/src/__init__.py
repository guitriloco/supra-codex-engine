"""
Supra-Codex Engine — Python Bindings for WraithEngine

Provides a Pythonic interface to the C++ WraithEngine core.
When compiled, subpackage `wraith/` will contain the pybind11
native module. Until then, this package provides a pure-Python
reference implementation that mirrors the C++ API.
"""

from .wraith.engine import WraithEngine, TaskConfig, TaskResult
from .wraith.scheduler import Scheduler

__all__ = [
    "WraithEngine",
    "TaskConfig",
    "TaskResult",
    "Scheduler",
]

__version__ = "0.1.0"