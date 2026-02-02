"""
Replay Engine.

Replays negotiation sessions from JSONL log files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, Callable

from ..core.events import Event
from ..domain.models import GameSpec, Offer


class ReplayEngine:
    """
    Replays logged negotiation sessions.
    
    Features:
    - Load and parse JSONL log files
    - Step-by-step or continuous replay
    - Event callbacks for integration
    """
    
    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        
        if not self.log_path.exists():
            raise FileNotFoundError(f"Log file not found: {log_path}")
        
        self._records: list[dict] = []
        self._metadata: dict = {}
        self._game_config: Optional[dict] = None
        self._result: Optional[dict] = None
        
        self._load_log()
    
    def _load_log(self):
        """Load and parse the log file."""
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                record = json.loads(line)
                record_type = record.get("type")
                
                if record_type == "session_start":
                    self._metadata["session_id"] = record.get("session_id")
                    self._metadata["start_time"] = record.get("timestamp")
                elif record_type == "session_end":
                    self._metadata["end_time"] = record.get("timestamp")
                    self._metadata["total_events"] = record.get("total_events")
                elif record_type == "game_config":
                    self._game_config = record.get("config")
                elif record_type == "result":
                    self._result = record
                elif record_type == "metadata":
                    self._metadata[record.get("key")] = record.get("value")
                elif record_type == "event":
                    self._records.append(record)
    
    @property
    def session_id(self) -> Optional[str]:
        """Get the session ID."""
        return self._metadata.get("session_id")
    
    @property
    def event_count(self) -> int:
        """Get number of events in the log."""
        return len(self._records)
    
    @property
    def game_config(self) -> Optional[dict]:
        """Get game configuration if logged."""
        return self._game_config
    
    @property
    def result(self) -> Optional[dict]:
        """Get negotiation result if logged."""
        return self._result
    
    @property
    def metadata(self) -> dict:
        """Get session metadata."""
        return self._metadata
    
    def get_events(self) -> Generator[Event, None, None]:
        """Iterate through all events."""
        for record in self._records:
            event_data = record.get("event_data", {})
            yield Event.from_dict(event_data)
    
    def get_event_at(self, index: int) -> Optional[Event]:
        """Get event at specific index."""
        if 0 <= index < len(self._records):
            event_data = self._records[index].get("event_data", {})
            return Event.from_dict(event_data)
        return None
    
    def replay(
        self,
        on_event: Callable[[Event, int], None],
        delay_ms: int = 0,
        real_time: bool = False,
    ) -> None:
        """
        Replay all events.
        
        Args:
            on_event: Callback for each event (event, index)
            delay_ms: Fixed delay between events (0 = no delay)
            real_time: If True, use actual time gaps from log
        """
        import time
        
        last_timestamp = None
        
        for i, record in enumerate(self._records):
            event_data = record.get("event_data", {})
            event = Event.from_dict(event_data)
            
            # Handle timing
            if real_time and last_timestamp:
                current_timestamp = event.timestamp
                gap = current_timestamp - last_timestamp
                if gap > 0:
                    time.sleep(gap)
                last_timestamp = current_timestamp
            elif delay_ms > 0:
                time.sleep(delay_ms / 1000.0)
            
            if last_timestamp is None:
                last_timestamp = event.timestamp
            
            # Call handler
            on_event(event, i)
    
    def get_offers(self) -> list[tuple[str, Offer]]:
        """Get all offers from the log."""
        offers = []
        
        for event in self.get_events():
            offer_dict = event.get_offer()
            if offer_dict:
                offer = Offer.from_dict(offer_dict)
                offers.append((event.sender_id, offer))
        
        return offers
    
    def get_messages(self) -> list[tuple[str, str]]:
        """Get all messages from the log."""
        messages = []
        
        for event in self.get_events():
            text = event.get_text()
            if text:
                messages.append((event.sender_id, text))
        
        return messages
    
    def get_summary(self) -> dict:
        """Get a summary of the session."""
        from ..core.events import EventType, HUMAN_ID, AGENT_ID
        
        events = list(self.get_events())
        
        human_offers = sum(1 for e in events if e.event_type == EventType.SEND_OFFER and e.sender_id == HUMAN_ID)
        agent_offers = sum(1 for e in events if e.event_type == EventType.SEND_OFFER and e.sender_id == AGENT_ID)
        human_messages = sum(1 for e in events if e.event_type == EventType.SEND_MESSAGE and e.sender_id == HUMAN_ID)
        agent_messages = sum(1 for e in events if e.event_type == EventType.SEND_MESSAGE and e.sender_id == AGENT_ID)
        
        return {
            "session_id": self.session_id,
            "total_events": len(events),
            "human_offers": human_offers,
            "agent_offers": agent_offers,
            "human_messages": human_messages,
            "agent_messages": agent_messages,
            "result": self._result,
        }


def load_replay(log_path: str) -> ReplayEngine:
    """Convenience function to load a replay."""
    return ReplayEngine(log_path)

