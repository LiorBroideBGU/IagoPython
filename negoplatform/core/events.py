"""
Event types and payloads for the negotiation platform.

Mirrors IAGO's event system:
- SEND_MESSAGE: Chat messages with various subtypes
- SEND_OFFER: Proposal of item allocations
- SEND_EXPRESSION: Emotional expressions
- OFFER_IN_PROGRESS: User is editing an offer
- TIME: Periodic time ticks
- FORMAL_ACCEPT: Binding acceptance of current allocation
- GAME_START / GAME_END: Session lifecycle
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time
import uuid


class EventType(Enum):
    """Types of events in the negotiation system."""
    SEND_MESSAGE = "send_message"
    SEND_OFFER = "send_offer"
    SEND_EXPRESSION = "send_expression"
    OFFER_IN_PROGRESS = "offer_in_progress"
    TIME = "time"
    FORMAL_ACCEPT = "formal_accept"
    GAME_START = "game_start"
    GAME_END = "game_end"


class MessageSubtype(Enum):
    """
    Subtypes for SEND_MESSAGE events.
    
    Matches IAGO's Event.SubClass for messages.
    """
    GENERIC = "generic"
    
    # Offer-related
    OFFER_PROPOSE = "offer_propose"
    OFFER_ACCEPT = "offer_accept"
    OFFER_REJECT = "offer_reject"
    
    # Preference-related
    PREF_INFO = "pref_info"  # Statement about preferences
    PREF_REQUEST = "pref_request"  # Question about preferences
    PREF_SPECIFIC_REQUEST = "pref_specific_request"  # Specific preference question
    PREF_WITHHOLD = "pref_withhold"  # Refusing to share preferences
    
    # Timing
    TIMING_REQUEST = "timing_request"  # Asking to hurry/slow down
    TIMING_INFO = "timing_info"  # Info about time
    
    # Social
    GREETING = "greeting"
    FAREWELL = "farewell"
    THANKS = "thanks"
    APOLOGY = "apology"
    THREAT = "threat"
    PROMISE = "promise"
    
    # Meta
    CONFIRMATION = "confirmation"
    CLARIFICATION = "clarification"


class Expression(Enum):
    """
    Emotional expressions available.
    
    IAGO provides 8 expressions for agents, 5 for humans.
    """
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    # Extended set (agent-only in IAGO)
    DISGUSTED = "disgusted"
    SCARED = "scared"
    CONTEMPT = "contempt"
    
    @classmethod
    def human_expressions(cls) -> list["Expression"]:
        """Expressions available to human users."""
        return [cls.NEUTRAL, cls.HAPPY, cls.SAD, cls.ANGRY, cls.SURPRISED]
    
    @classmethod
    def agent_expressions(cls) -> list["Expression"]:
        """All expressions available to agents."""
        return list(cls)


@dataclass
class Preference:
    """
    Structured preference information.
    
    Used in PREF_* messages to encode preferences like:
    - "I like apples more than oranges" (issue1=apples, issue2=oranges, relation=GREATER)
    - "Apples are my favorite" (issue1=apples, issue2=None, relation=BEST)
    """
    issue1: str
    issue2: Optional[str]  # None for BEST/WORST relations
    relation: str  # GREATER, LESS, EQUAL, BEST, WORST
    is_query: bool = False  # True if this is a question
    
    def to_dict(self) -> dict:
        return {
            "issue1": self.issue1,
            "issue2": self.issue2,
            "relation": self.relation,
            "is_query": self.is_query,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Preference":
        return cls(
            issue1=data["issue1"],
            issue2=data.get("issue2"),
            relation=data["relation"],
            is_query=data.get("is_query", False),
        )


# Sender ID constants
HUMAN_ID = "human"
AGENT_ID = "agent"
SYSTEM_ID = "system"


@dataclass
class Event:
    """
    A single event in the negotiation.
    
    All events have:
    - Unique ID
    - Type (from EventType enum)
    - Sender ID (human, agent, or system)
    - Timestamp
    - Optional payload depending on type
    - Optional delay (for agent responses)
    """
    event_type: EventType
    sender_id: str
    payload: dict = field(default_factory=dict)
    delay_ms: int = 0  # Milliseconds to wait before executing
    
    # Auto-generated fields
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    
    # Optional subtype for messages
    subtype: Optional[MessageSubtype] = None
    
    def __post_init__(self):
        # Validate payload based on type
        pass
    
    @classmethod
    def send_message(
        cls,
        sender_id: str,
        text: str,
        subtype: MessageSubtype = MessageSubtype.GENERIC,
        preference: Optional[Preference] = None,
        delay_ms: int = 0,
    ) -> "Event":
        """Create a SEND_MESSAGE event."""
        payload = {"text": text}
        if preference:
            payload["preference"] = preference.to_dict()
        return cls(
            event_type=EventType.SEND_MESSAGE,
            sender_id=sender_id,
            payload=payload,
            subtype=subtype,
            delay_ms=delay_ms,
        )
    
    @classmethod
    def send_offer(
        cls,
        sender_id: str,
        offer_dict: dict,
        delay_ms: int = 0,
    ) -> "Event":
        """Create a SEND_OFFER event."""
        return cls(
            event_type=EventType.SEND_OFFER,
            sender_id=sender_id,
            payload={"offer": offer_dict},
            delay_ms=delay_ms,
        )
    
    @classmethod
    def send_expression(
        cls,
        sender_id: str,
        expression: Expression,
        duration_ms: int = 2000,
        delay_ms: int = 0,
    ) -> "Event":
        """Create a SEND_EXPRESSION event."""
        return cls(
            event_type=EventType.SEND_EXPRESSION,
            sender_id=sender_id,
            payload={"expression": expression.value, "duration_ms": duration_ms},
            delay_ms=delay_ms,
        )
    
    @classmethod
    def offer_in_progress(
        cls,
        sender_id: str,
        partial_offer_dict: Optional[dict] = None,
    ) -> "Event":
        """Create an OFFER_IN_PROGRESS event."""
        payload = {}
        if partial_offer_dict:
            payload["partial_offer"] = partial_offer_dict
        return cls(
            event_type=EventType.OFFER_IN_PROGRESS,
            sender_id=sender_id,
            payload=payload,
        )
    
    @classmethod
    def time_tick(cls, elapsed_seconds: float, remaining_seconds: Optional[float] = None) -> "Event":
        """Create a TIME event."""
        payload = {"elapsed_seconds": elapsed_seconds}
        if remaining_seconds is not None:
            payload["remaining_seconds"] = remaining_seconds
        return cls(
            event_type=EventType.TIME,
            sender_id=SYSTEM_ID,
            payload=payload,
        )
    
    @classmethod
    def formal_accept(cls, sender_id: str, delay_ms: int = 0) -> "Event":
        """Create a FORMAL_ACCEPT event."""
        return cls(
            event_type=EventType.FORMAL_ACCEPT,
            sender_id=sender_id,
            payload={},
            delay_ms=delay_ms,
        )
    
    @classmethod
    def game_start(cls, game_name: str, game_index: int = 0) -> "Event":
        """Create a GAME_START event."""
        return cls(
            event_type=EventType.GAME_START,
            sender_id=SYSTEM_ID,
            payload={"game_name": game_name, "game_index": game_index},
        )
    
    @classmethod
    def game_end(cls, reason: str, final_offer_dict: Optional[dict] = None) -> "Event":
        """Create a GAME_END event."""
        payload = {"reason": reason}
        if final_offer_dict:
            payload["final_offer"] = final_offer_dict
        return cls(
            event_type=EventType.GAME_END,
            sender_id=SYSTEM_ID,
            payload=payload,
        )
    
    def get_text(self) -> Optional[str]:
        """Get message text if this is a SEND_MESSAGE event."""
        if self.event_type == EventType.SEND_MESSAGE:
            return self.payload.get("text")
        return None
    
    def get_offer(self) -> Optional[dict]:
        """Get offer dict if this is a SEND_OFFER event."""
        if self.event_type == EventType.SEND_OFFER:
            return self.payload.get("offer")
        return None
    
    def get_expression(self) -> Optional[str]:
        """Get expression value if this is a SEND_EXPRESSION event."""
        if self.event_type == EventType.SEND_EXPRESSION:
            return self.payload.get("expression")
        return None
    
    def get_preference(self) -> Optional[Preference]:
        """Get preference if this message has one."""
        if self.event_type == EventType.SEND_MESSAGE:
            pref_data = self.payload.get("preference")
            if pref_data:
                return Preference.from_dict(pref_data)
        return None
    
    def to_dict(self) -> dict:
        """Serialize event to dictionary for logging."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "sender_id": self.sender_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "subtype": self.subtype.value if self.subtype else None,
            "delay_ms": self.delay_ms,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """Deserialize event from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            sender_id=data["sender_id"],
            timestamp=data["timestamp"],
            payload=data.get("payload", {}),
            subtype=MessageSubtype(data["subtype"]) if data.get("subtype") else None,
            delay_ms=data.get("delay_ms", 0),
        )

