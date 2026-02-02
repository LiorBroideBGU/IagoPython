"""
Negotiation Session management.

Tracks the state of a negotiation including:
- Current offer on the board
- Event history
- Formal acceptances
- Time tracking
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time

from ..domain.models import GameSpec, Offer, Party
from .events import Event, EventType, HUMAN_ID, AGENT_ID


class SessionState(Enum):
    """State of the negotiation session."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass
class FormalAcceptance:
    """Tracks formal acceptances."""
    human_accepted: bool = False
    agent_accepted: bool = False
    human_accepted_at: Optional[float] = None
    agent_accepted_at: Optional[float] = None
    
    def reset(self):
        """Reset acceptances (called when offer changes)."""
        self.human_accepted = False
        self.agent_accepted = False
        self.human_accepted_at = None
        self.agent_accepted_at = None
    
    def both_accepted(self) -> bool:
        return self.human_accepted and self.agent_accepted


@dataclass
class NegotiationHistory:
    """Maintains history of all events in the negotiation."""
    events: list[Event] = field(default_factory=list)
    
    def add(self, event: Event) -> None:
        self.events.append(event)
    
    def get_all(self) -> list[Event]:
        return list(self.events)
    
    def get_by_type(self, event_type: EventType) -> list[Event]:
        return [e for e in self.events if e.event_type == event_type]
    
    def get_by_sender(self, sender_id: str) -> list[Event]:
        return [e for e in self.events if e.sender_id == sender_id]
    
    def get_human_events(self) -> list[Event]:
        return self.get_by_sender(HUMAN_ID)
    
    def get_agent_events(self) -> list[Event]:
        return self.get_by_sender(AGENT_ID)
    
    def get_last(self, count: int = 1) -> list[Event]:
        return self.events[-count:] if self.events else []
    
    def get_last_offer(self) -> Optional[Event]:
        """Get the most recent SEND_OFFER event."""
        offers = self.get_by_type(EventType.SEND_OFFER)
        return offers[-1] if offers else None
    
    def get_last_human_offer(self) -> Optional[Event]:
        """Get the most recent offer from human."""
        offers = [
            e for e in self.events 
            if e.event_type == EventType.SEND_OFFER and e.sender_id == HUMAN_ID
        ]
        return offers[-1] if offers else None
    
    def get_last_agent_offer(self) -> Optional[Event]:
        """Get the most recent offer from agent."""
        offers = [
            e for e in self.events 
            if e.event_type == EventType.SEND_OFFER and e.sender_id == AGENT_ID
        ]
        return offers[-1] if offers else None
    
    def get_messages(self) -> list[Event]:
        return self.get_by_type(EventType.SEND_MESSAGE)
    
    def get_offer_count(self) -> int:
        return len(self.get_by_type(EventType.SEND_OFFER))
    
    def get_time_since_last_event(self, exclude_time_events: bool = True) -> Optional[float]:
        """Get seconds since last event (optionally excluding TIME events)."""
        if not self.events:
            return None
        
        events = self.events
        if exclude_time_events:
            events = [e for e in events if e.event_type != EventType.TIME]
        
        if not events:
            return None
        
        return time.time() - events[-1].timestamp
    
    def clear(self) -> None:
        self.events.clear()


class NegotiationSession:
    """
    Manages the state of a single negotiation.
    
    Responsibilities:
    - Track current offer state
    - Manage event history
    - Track formal acceptances
    - Validate state transitions
    - Calculate utilities
    """
    
    def __init__(self, game: GameSpec, session_id: Optional[str] = None):
        self.game = game
        self.session_id = session_id or str(int(time.time()))
        
        # State
        self._state = SessionState.NOT_STARTED
        self._current_offer: Offer = game.create_initial_offer()
        self._acceptance = FormalAcceptance()
        
        # History
        self._history = NegotiationHistory()
        
        # Timing
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        
        # Last sent offers (for tracking)
        self._last_human_offer: Optional[Offer] = None
        self._last_agent_offer: Optional[Offer] = None
    
    @property
    def state(self) -> SessionState:
        return self._state
    
    @property
    def current_offer(self) -> Offer:
        return self._current_offer
    
    @property
    def history(self) -> NegotiationHistory:
        return self._history
    
    @property
    def acceptance(self) -> FormalAcceptance:
        return self._acceptance
    
    @property
    def is_active(self) -> bool:
        return self._state == SessionState.IN_PROGRESS
    
    def start(self) -> Event:
        """Start the negotiation session."""
        if self._state != SessionState.NOT_STARTED:
            raise RuntimeError(f"Cannot start session in state {self._state}")
        
        self._state = SessionState.IN_PROGRESS
        self._start_time = time.time()
        
        event = Event.game_start(self.game.name)
        self._history.add(event)
        return event
    
    def apply_event(self, event: Event) -> None:
        """
        Apply an event to the session state.
        
        Updates history and state based on event type.
        """
        if not self.is_active and event.event_type not in (
            EventType.GAME_START, EventType.TIME
        ):
            return  # Ignore events when not active
        
        # Add to history
        self._history.add(event)
        
        # Update state based on event type
        if event.event_type == EventType.SEND_OFFER:
            self._handle_offer(event)
        elif event.event_type == EventType.FORMAL_ACCEPT:
            self._handle_formal_accept(event)
        elif event.event_type == EventType.GAME_END:
            self._handle_game_end(event)
    
    def _handle_offer(self, event: Event) -> None:
        """Handle SEND_OFFER event."""
        offer_dict = event.get_offer()
        if offer_dict:
            offer = Offer.from_dict(offer_dict)
            
            # Validate offer
            is_valid, error = self.game.validate_offer(offer)
            if not is_valid:
                print(f"Invalid offer: {error}")
                return
            
            # Update current offer
            self._current_offer = offer
            
            # Track who sent it
            if event.sender_id == HUMAN_ID:
                self._last_human_offer = offer
            else:
                self._last_agent_offer = offer
            
            # Reset formal acceptances when offer changes
            self._acceptance.reset()
    
    def _handle_formal_accept(self, event: Event) -> None:
        """Handle FORMAL_ACCEPT event."""
        # Only valid if offer is complete
        if not self._current_offer.is_complete():
            print("Cannot formally accept incomplete offer")
            return
        
        if event.sender_id == HUMAN_ID:
            self._acceptance.human_accepted = True
            self._acceptance.human_accepted_at = event.timestamp
        else:
            self._acceptance.agent_accepted = True
            self._acceptance.agent_accepted_at = event.timestamp
        
        # Check if negotiation is complete
        if self._acceptance.both_accepted():
            self._complete_negotiation("mutual_agreement")
    
    def _handle_game_end(self, event: Event) -> None:
        """Handle GAME_END event."""
        reason = event.payload.get("reason", "unknown")
        self._complete_negotiation(reason)
    
    def _complete_negotiation(self, reason: str) -> None:
        """Mark negotiation as complete."""
        if reason == "timeout":
            self._state = SessionState.TIMED_OUT
        elif reason == "cancelled":
            self._state = SessionState.CANCELLED
        else:
            self._state = SessionState.COMPLETED
        
        self._end_time = time.time()
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self._start_time is None:
            return 0.0
        end = self._end_time or time.time()
        return end - self._start_time
    
    def get_remaining_time(self) -> Optional[float]:
        """Get remaining time in seconds, or None if no deadline."""
        if not self.game.rules.has_deadline():
            return None
        deadline = self.game.rules.deadline_seconds
        elapsed = self.get_elapsed_time()
        return max(0, deadline - elapsed)
    
    def is_timed_out(self) -> bool:
        """Check if deadline has passed."""
        remaining = self.get_remaining_time()
        return remaining is not None and remaining <= 0
    
    def get_human_utility(self, offer: Optional[Offer] = None) -> float:
        """Calculate human's utility for an offer (default: current offer)."""
        offer = offer or self._current_offer
        return self.game.human_utility.calculate(offer)
    
    def get_agent_utility(self, offer: Optional[Offer] = None) -> float:
        """Calculate agent's utility for an offer (default: current offer)."""
        offer = offer or self._current_offer
        return self.game.agent_utility.calculate(offer)
    
    def get_utilities(self, offer: Optional[Offer] = None) -> tuple[float, float]:
        """Get (human_utility, agent_utility) for an offer."""
        return (self.get_human_utility(offer), self.get_agent_utility(offer))
    
    def get_utility_percentages(self, offer: Optional[Offer] = None) -> tuple[float, float]:
        """Get utilities as percentages of max possible."""
        offer = offer or self._current_offer
        human_max = self.game.human_utility.get_max_possible(self.game.issues)
        agent_max = self.game.agent_utility.get_max_possible(self.game.issues)
        
        human_pct = (self.get_human_utility(offer) / human_max * 100) if human_max else 0
        agent_pct = (self.get_agent_utility(offer) / agent_max * 100) if agent_max else 0
        
        return (human_pct, agent_pct)
    
    def can_formally_accept(self) -> bool:
        """Check if formal accept is currently valid."""
        return self.is_active and self._current_offer.is_complete()
    
    def get_summary(self) -> dict:
        """Get summary of session state for logging/display."""
        return {
            "session_id": self.session_id,
            "game_name": self.game.name,
            "state": self._state.value,
            "elapsed_seconds": self.get_elapsed_time(),
            "remaining_seconds": self.get_remaining_time(),
            "offer_count": self._history.get_offer_count(),
            "message_count": len(self._history.get_messages()),
            "human_accepted": self._acceptance.human_accepted,
            "agent_accepted": self._acceptance.agent_accepted,
            "current_offer": self._current_offer.to_dict() if self._current_offer else None,
            "human_utility": self.get_human_utility(),
            "agent_utility": self.get_agent_utility(),
        }

