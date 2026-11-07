"""
webui/jobs/adapters/base.py — Abstract base interface for stage execution adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List


class BaseStageAdapter(ABC):
    """Abstract base class for executing a pipeline stage via the WebUI job runner."""

    @abstractmethod
    def run(
        self,
        script_ids: List[str],
        options: Dict[str, Any],
        emit_log: Callable[[str], None],
        emit_progress: Callable[[int, int, str], None],
        check_cancelled: Callable[[], bool],
    ) -> Dict[str, Any]:
        """
        Executes the stage for the given script_ids.
        
        Args:
            script_ids: Target script IDs to process.
            options: Stage-specific options (e.g. force=True, seed=123).
            emit_log: Callback to append a line to the job's log feed.
            emit_progress: Callback to report (current_count, total_count, current_script_id).
            check_cancelled: Function returning True if the job was cancelled by user.

        Returns:
            Dict containing summary results (e.g. success_count, failed_ids).
        """
        ...

