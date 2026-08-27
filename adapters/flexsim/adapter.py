"""FlexSim Adapter interface.

Scaffolding only, not implemented. See adapters/README.md.

The endpoints it's meant to sit in front of already exist and work
today in bridge/app/api/telemetry.py and bridge/app/api/commands.py:
this adapter's job is just to translate between bridge/'s wire format
and rms/domain's Robot/Task types, so the Fleet Manager and Resource
Scheduler don't talk HTTP directly.
"""

from __future__ import annotations

from rms.domain import Robot


class FlexSimAdapter:
    """Reads FlexSim state from the bridge and (eventually) forwards
    RMS commands to it via POST /api/v1/commands.
    """

    def __init__(self, bridge_url: str = "http://127.0.0.1:8000") -> None:
        self.bridge_url = bridge_url

    def get_robots(self) -> list[Robot]:
        """Fetch GET /api/v1/state and map its robots into rms/domain
        Robot objects.
        """
        raise NotImplementedError

    def send_command(self, command_type: str, payload: dict) -> str:
        """POST /api/v1/commands and return the command id for the RMS
        to track through poll/ack.
        """
        raise NotImplementedError
