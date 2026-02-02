"""
Core domain models for the negotiation platform.

Matches IAGO's representation:
- Issues with quantities
- Offers as 3-row allocations (agent/middle/human)
- Utility functions for scoring
- Protocol rules for game constraints
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Party(Enum):
    """Identifies negotiation parties."""
    AGENT = "agent"
    HUMAN = "human"


@dataclass
class Issue:
    """
    A single negotiable issue (e.g., 'apples', 'salary').
    
    Attributes:
        name: Unique identifier for the issue
        display_name: Human-readable name (plural form)
        quantity: Total number of units available
        divisible: Whether partial units are allowed
    """
    name: str
    display_name: str
    quantity: int
    divisible: bool = False
    
    def __post_init__(self):
        if self.quantity < 1:
            raise ValueError(f"Issue quantity must be at least 1, got {self.quantity}")


@dataclass
class Allocation:
    """
    Allocation of a single issue across the 3-row board.
    
    IAGO uses [agent_count, middle_count, human_count] format.
    Middle items are undecided/unallocated.
    """
    agent: int
    middle: int
    human: int
    
    def __post_init__(self):
        if any(x < 0 for x in [self.agent, self.middle, self.human]):
            raise ValueError("Allocation values cannot be negative")
    
    @property
    def total(self) -> int:
        return self.agent + self.middle + self.human
    
    def is_complete(self) -> bool:
        """Returns True if no items remain in the middle."""
        return self.middle == 0
    
    def to_tuple(self) -> tuple[int, int, int]:
        return (self.agent, self.middle, self.human)
    
    @classmethod
    def from_tuple(cls, t: tuple[int, int, int]) -> "Allocation":
        return cls(agent=t[0], middle=t[1], human=t[2])
    
    @classmethod
    def all_to_agent(cls, quantity: int) -> "Allocation":
        return cls(agent=quantity, middle=0, human=0)
    
    @classmethod
    def all_to_human(cls, quantity: int) -> "Allocation":
        return cls(agent=0, middle=0, human=quantity)
    
    @classmethod
    def all_in_middle(cls, quantity: int) -> "Allocation":
        return cls(agent=0, middle=quantity, human=0)
    
    @classmethod
    def split_even(cls, quantity: int) -> "Allocation":
        """Split evenly, remainder goes to middle."""
        each = quantity // 2
        remainder = quantity - (each * 2)
        return cls(agent=each, middle=remainder, human=each)


@dataclass
class Offer:
    """
    A negotiation offer representing allocation of all issues.
    
    Supports partial offers where some issues may be unset (None).
    This is essential for NegoChat's issue-by-issue negotiation.
    """
    allocations: dict[str, Optional[Allocation]] = field(default_factory=dict)
    
    def __getitem__(self, issue_name: str) -> Optional[Allocation]:
        return self.allocations.get(issue_name)
    
    def __setitem__(self, issue_name: str, allocation: Optional[Allocation]):
        self.allocations[issue_name] = allocation
    
    def is_complete(self) -> bool:
        """
        Returns True if all issues are allocated with nothing in the middle.
        Required for FORMAL_ACCEPT to be valid.
        """
        if not self.allocations:
            return False
        return all(
            alloc is not None and alloc.is_complete() 
            for alloc in self.allocations.values()
        )
    
    def is_partial(self) -> bool:
        """Returns True if some issues are unset or have items in middle."""
        return not self.is_complete()
    
    def get_allocated_issues(self) -> list[str]:
        """Returns list of issues that have been allocated (not None)."""
        return [
            name for name, alloc in self.allocations.items() 
            if alloc is not None
        ]
    
    def get_complete_issues(self) -> list[str]:
        """Returns list of issues fully allocated (nothing in middle)."""
        return [
            name for name, alloc in self.allocations.items() 
            if alloc is not None and alloc.is_complete()
        ]
    
    def copy(self) -> "Offer":
        """Create a deep copy of this offer."""
        new_allocations = {
            name: Allocation(alloc.agent, alloc.middle, alloc.human) if alloc else None
            for name, alloc in self.allocations.items()
        }
        return Offer(allocations=new_allocations)
    
    @classmethod
    def empty(cls, issue_names: list[str]) -> "Offer":
        """Create an offer with all issues unset."""
        return cls(allocations={name: None for name in issue_names})
    
    @classmethod
    def all_in_middle(cls, issues: list[Issue]) -> "Offer":
        """Create an offer with all items in the middle (starting state)."""
        return cls(allocations={
            issue.name: Allocation.all_in_middle(issue.quantity)
            for issue in issues
        })
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON/logging."""
        return {
            name: alloc.to_tuple() if alloc else None
            for name, alloc in self.allocations.items()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Offer":
        """Deserialize from dictionary."""
        return cls(allocations={
            name: Allocation.from_tuple(tuple(val)) if val else None
            for name, val in data.items()
        })


@dataclass
class UtilityFunction:
    """
    Calculates utility (score) for a party based on item values.
    
    Each party has different valuations for each issue.
    """
    party: Party
    values: dict[str, float]  # issue_name -> value per unit
    
    def calculate(self, offer: Offer) -> float:
        """Calculate total utility for this party from an offer."""
        total = 0.0
        for issue_name, allocation in offer.allocations.items():
            if allocation is None:
                continue
            value_per_unit = self.values.get(issue_name, 0.0)
            if self.party == Party.AGENT:
                total += allocation.agent * value_per_unit
            else:
                total += allocation.human * value_per_unit
        return total
    
    def get_max_possible(self, issues: list[Issue]) -> float:
        """Calculate maximum possible utility (all items to this party)."""
        return sum(
            issue.quantity * self.values.get(issue.name, 0.0)
            for issue in issues
        )
    
    def get_issue_priority(self) -> list[str]:
        """Return issues sorted by value (highest first)."""
        return sorted(self.values.keys(), key=lambda k: self.values[k], reverse=True)
    
    def get_best_issue(self) -> str:
        """Return the highest-valued issue."""
        return max(self.values.keys(), key=lambda k: self.values[k])
    
    def get_worst_issue(self) -> str:
        """Return the lowest-valued issue."""
        return min(self.values.keys(), key=lambda k: self.values[k])


@dataclass
class ProtocolRules:
    """
    Rules governing the negotiation protocol.
    """
    deadline_seconds: Optional[int] = 300  # 5 minutes default, None = no deadline
    allow_partial_agreements: bool = True  # Can issues be agreed individually?
    require_formal_accept: bool = True  # Must both parties formally accept?
    time_tick_interval_ms: int = 5000  # TIME events every 5 seconds
    
    def has_deadline(self) -> bool:
        return self.deadline_seconds is not None


@dataclass
class GameSpec:
    """
    Complete specification of a negotiation game.
    
    Includes issues, utility functions for both parties, and protocol rules.
    """
    name: str
    description: str
    issues: list[Issue]
    agent_utility: UtilityFunction
    human_utility: UtilityFunction
    rules: ProtocolRules = field(default_factory=ProtocolRules)
    
    # Display configuration
    issue_singular_names: dict[str, str] = field(default_factory=dict)
    issue_plural_names: dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        # Validate that all issues have utility values
        issue_names = {issue.name for issue in self.issues}
        agent_issues = set(self.agent_utility.values.keys())
        human_issues = set(self.human_utility.values.keys())
        
        if issue_names != agent_issues:
            missing = issue_names - agent_issues
            extra = agent_issues - issue_names
            raise ValueError(f"Agent utility mismatch. Missing: {missing}, Extra: {extra}")
        
        if issue_names != human_issues:
            missing = issue_names - human_issues
            extra = human_issues - issue_names
            raise ValueError(f"Human utility mismatch. Missing: {missing}, Extra: {extra}")
        
        # Set default display names
        for issue in self.issues:
            if issue.name not in self.issue_singular_names:
                self.issue_singular_names[issue.name] = issue.name
            if issue.name not in self.issue_plural_names:
                self.issue_plural_names[issue.name] = issue.display_name
    
    def get_issue(self, name: str) -> Optional[Issue]:
        """Get issue by name."""
        for issue in self.issues:
            if issue.name == name:
                return issue
        return None
    
    def get_issue_names(self) -> list[str]:
        """Get list of all issue names."""
        return [issue.name for issue in self.issues]
    
    def get_num_issues(self) -> int:
        return len(self.issues)
    
    def create_initial_offer(self) -> Offer:
        """Create the starting offer with all items in middle."""
        return Offer.all_in_middle(self.issues)
    
    def get_total_items(self) -> int:
        """Get total number of items across all issues."""
        return sum(issue.quantity for issue in self.issues)
    
    def validate_offer(self, offer: Offer) -> tuple[bool, str]:
        """
        Validate that an offer is legal for this game.
        Returns (is_valid, error_message).
        """
        for issue in self.issues:
            alloc = offer[issue.name]
            if alloc is None:
                continue  # Partial offers allowed
            if alloc.total != issue.quantity:
                return False, f"Issue '{issue.name}' has {alloc.total} items, expected {issue.quantity}"
        return True, ""

