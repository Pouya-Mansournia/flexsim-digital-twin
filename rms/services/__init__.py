"""Cross-cutting RMS services that coordinate multiple managers.

Unlike rms/missions, rms/tasks, etc. (one manager, one responsibility),
this package holds things that need several of them at once, such as
the end-to-end scheduling orchestration in orchestrator.py.
"""

from .orchestrator import IntegrationError, OrchestrationResult, RmsOrchestrator

__all__ = ["IntegrationError", "OrchestrationResult", "RmsOrchestrator"]
