"""
Agent Context: read-only view of session state for agents.

Provides agents with all the information they need to make decisions
without giving them direct access to modify session state.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.models import GameSpec, Offer, Issue, UtilityFunction
    from ..core.session import NegotiationHistory


@dataclass
class AgentContext:
    """
    Read-only context provided to agents on each event.
    
    Contains everything an agent needs to know about the current
    negotiation state to make a decision.
    """
    
    # Game information
    game: "GameSpec"
    
    # Agent's own utility function
    agent_utility: "UtilityFunction"
    
    # Opponent's utility function (may be estimated or real)
    opponent_utility: "UtilityFunction"
    
    # Current state
    current_offer: "Offer"
    
    # History
    history: "NegotiationHistory"
    
    # Timing
    elapsed_seconds: float
    remaining_seconds: Optional[float]
    
    # Acceptance state
    human_has_accepted: bool
    agent_has_accepted: bool
    
    # Session info
    session_id: str
    game_index: int = 0  # For repeated games
    
    # Convenience properties
    
    @property
    def issues(self) -> list["Issue"]:
        """Get all issues in the game."""
        return self.game.issues
    
    @property
    def issue_names(self) -> list[str]:
        """Get names of all issues."""
        return self.game.get_issue_names()
    
    @property
    def num_issues(self) -> int:
        """Get number of issues."""
        return len(self.game.issues)
    
    def get_issue(self, name: str) -> Optional["Issue"]:
        """Get issue by name."""
        return self.game.get_issue(name)
    
    # Utility calculations
    
    def get_agent_utility(self, offer: Optional["Offer"] = None) -> float:
        """Calculate agent's utility for an offer."""
        offer = offer or self.current_offer
        return self.agent_utility.calculate(offer)
    
    def get_opponent_utility(self, offer: Optional["Offer"] = None) -> float:
        """Calculate opponent's utility for an offer."""
        offer = offer or self.current_offer
        return self.opponent_utility.calculate(offer)
    
    def get_max_agent_utility(self) -> float:
        """Get maximum possible agent utility."""
        return self.agent_utility.get_max_possible(self.game.issues)
    
    def get_max_opponent_utility(self) -> float:
        """Get maximum possible opponent utility."""
        return self.opponent_utility.get_max_possible(self.game.issues)
    
    def get_agent_utility_percent(self, offer: Optional["Offer"] = None) -> float:
        """Get agent utility as percentage of max."""
        max_util = self.get_max_agent_utility()
        if max_util == 0:
            return 0.0
        return (self.get_agent_utility(offer) / max_util) * 100
    
    def get_opponent_utility_percent(self, offer: Optional["Offer"] = None) -> float:
        """Get opponent utility as percentage of max."""
        max_util = self.get_max_opponent_utility()
        if max_util == 0:
            return 0.0
        return (self.get_opponent_utility(offer) / max_util) * 100
    
    # History queries
    
    def get_last_human_offer(self) -> Optional["Offer"]:
        """Get the last offer made by the human."""
        from ..domain.models import Offer
        event = self.history.get_last_human_offer()
        if event and event.get_offer():
            return Offer.from_dict(event.get_offer())
        return None
    
    def get_last_agent_offer(self) -> Optional["Offer"]:
        """Get the last offer made by the agent."""
        from ..domain.models import Offer
        event = self.history.get_last_agent_offer()
        if event and event.get_offer():
            return Offer.from_dict(event.get_offer())
        return None
    
    def get_offer_count(self) -> int:
        """Get total number of offers made."""
        return self.history.get_offer_count()
    
    def get_human_offer_count(self) -> int:
        """Get number of offers made by human."""
        from ..core.events import EventType, HUMAN_ID
        return len([
            e for e in self.history.get_by_type(EventType.SEND_OFFER)
            if e.sender_id == HUMAN_ID
        ])
    
    def get_agent_offer_count(self) -> int:
        """Get number of offers made by agent."""
        from ..core.events import EventType, AGENT_ID
        return len([
            e for e in self.history.get_by_type(EventType.SEND_OFFER)
            if e.sender_id == AGENT_ID
        ])
    
    def get_time_since_last_action(self) -> Optional[float]:
        """Get seconds since last non-TIME event."""
        return self.history.get_time_since_last_event(exclude_time_events=True)
    
    # Offer analysis
    
    def is_offer_complete(self, offer: Optional["Offer"] = None) -> bool:
        """Check if offer has all items allocated for all game issues."""
        offer = offer or self.current_offer
        for issue in self.game.issues:
            alloc = offer[issue.name]
            if alloc is None:
                return False
            if not alloc.is_complete():
                return False
        return True
    
    def can_formally_accept(self) -> bool:
        """Check if formal accept is currently valid.
        
        Requires all game issues to have allocations (can be partial - 
        items in middle are allowed and won't contribute to either party's score).
        """
        for issue in self.game.issues:
            alloc = self.current_offer[issue.name]
            if alloc is None:
                return False
        return True
    
    def is_offer_acceptable(
        self, 
        offer: Optional["Offer"] = None, 
        min_utility_percent: float = 40.0
    ) -> bool:
        """
        Check if an offer meets minimum acceptability threshold.
        
        Args:
            offer: Offer to evaluate (default: current)
            min_utility_percent: Minimum acceptable utility as % of max
        """
        return self.get_agent_utility_percent(offer) >= min_utility_percent
    
    def compare_offers(
        self, 
        offer1: "Offer", 
        offer2: "Offer"
    ) -> tuple[float, float]:
        """
        Compare two offers from agent's perspective.
        
        Returns (offer1_utility, offer2_utility).
        """
        return (
            self.get_agent_utility(offer1),
            self.get_agent_utility(offer2),
        )
    
    # Preference analysis
    
    def get_agent_preference_order(self) -> list[str]:
        """Get issues sorted by agent's preference (highest first)."""
        return self.agent_utility.get_issue_priority()
    
    def get_opponent_preference_order(self) -> list[str]:
        """Get issues sorted by opponent's preference (highest first)."""
        return self.opponent_utility.get_issue_priority()
    
    def get_agent_best_issue(self) -> str:
        """Get the issue agent values most."""
        return self.agent_utility.get_best_issue()
    
    def get_agent_worst_issue(self) -> str:
        """Get the issue agent values least."""
        return self.agent_utility.get_worst_issue()
    
    def get_display_name(self, issue_name: str, plural: bool = True) -> str:
        """Get human-readable name for an issue."""
        if plural:
            return self.game.issue_plural_names.get(issue_name, issue_name)
        return self.game.issue_singular_names.get(issue_name, issue_name)

