"""
Event Logger.

Logs all negotiation events to JSONL format for analysis and replay.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.events import Event
from ..core.bus import EventBus


class EventLogger:
    """
    Logs events to JSONL file.
    
    Features:
    - Automatic file creation with timestamp
    - Subscribes to EventBus for automatic logging
    - Includes session metadata
    """
    
    def __init__(
        self,
        output_dir: str = "logs",
        session_id: Optional[str] = None,
        auto_subscribe: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file
        self._file_path = self.output_dir / f"session_{self.session_id}.jsonl"
        self._file = open(self._file_path, "a", encoding="utf-8")
        
        self._event_count = 0
        self._event_bus: Optional[EventBus] = None
        
        # Write session header
        self._write_header()
    
    def _write_header(self):
        """Write session header to log file."""
        header = {
            "type": "session_start",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
        }
        self._write_line(header)
    
    def _write_line(self, data: dict):
        """Write a single line to the log file."""
        self._file.write(json.dumps(data) + "\n")
        self._file.flush()
    
    def subscribe_to_bus(self, event_bus: EventBus):
        """Subscribe to an event bus for automatic logging."""
        self._event_bus = event_bus
        event_bus.subscribe(
            self.log_event,
            subscriber_id="event_logger",
        )
    
    def log_event(self, event: Event):
        """Log a single event."""
        self._event_count += 1
        
        record = {
            "type": "event",
            "session_id": self.session_id,
            "event_number": self._event_count,
            "timestamp": datetime.fromtimestamp(event.timestamp).isoformat(),
            "event_data": event.to_dict(),
        }
        
        self._write_line(record)
    
    def log_action(self, action_type: str, action_data: dict, sender_id: str = "agent"):
        """Log an agent action (separate from event)."""
        record = {
            "type": "action",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "sender_id": sender_id,
            "action_type": action_type,
            "action_data": action_data,
        }
        
        self._write_line(record)
    
    def log_metadata(self, key: str, value: any):
        """Log arbitrary metadata."""
        record = {
            "type": "metadata",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "value": value,
        }
        
        self._write_line(record)
    
    def log_game_config(self, game_config: dict):
        """Log game configuration."""
        record = {
            "type": "game_config",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "config": game_config,
        }
        
        self._write_line(record)
    
    def log_result(
        self,
        outcome: str,
        human_utility: float,
        agent_utility: float,
        final_offer: Optional[dict] = None,
    ):
        """Log negotiation result."""
        record = {
            "type": "result",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
            "human_utility": human_utility,
            "agent_utility": agent_utility,
            "final_offer": final_offer,
            "total_events": self._event_count,
        }
        
        self._write_line(record)
    
    def close(self):
        """Close the log file."""
        if self._event_bus:
            self._event_bus.unsubscribe("event_logger")
        
        # Write session end marker
        end_record = {
            "type": "session_end",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_events": self._event_count,
        }
        self._write_line(end_record)
        
        self._file.close()
    
    @property
    def file_path(self) -> Path:
        """Get the log file path."""
        return self._file_path
    
    @property
    def event_count(self) -> int:
        """Get number of events logged."""
        return self._event_count
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

