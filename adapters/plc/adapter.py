"""PLC / Workstation Adapter interface.

Scaffolding only (Phase 6, not implemented). See adapters/README.md.

Meant to expose workstation state (READY/BUSY/BLOCKED/FAULT/STARVED/
OFFLINE) to the Workstation Manager over OPC UA, a PLC gateway, or a
vendor-specific REST/MQTT interface, protocol choice not yet made.
"""

from __future__ import annotations

from rms.domain import Workstation


class PlcAdapter:
    """Bridges the RMS to real workstation/PLC hardware."""

    def get_workstations(self) -> list[Workstation]:
        """Read current workstation state from the plant floor."""
        raise NotImplementedError

    def send_command(self, workstation_id: str, command_type: str) -> None:
        """Send a command to a workstation (e.g. release, hold)."""
        raise NotImplementedError
