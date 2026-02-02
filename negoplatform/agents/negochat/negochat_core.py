"""
NegoChat Core Algorithm.

Implements the issue-by-issue negotiation strategy from:
"NegoChat: A Chat-Based Negotiation Agent" (Rosenfeld et al.)

Key concepts:
- Stack A: Issues we value MORE than opponent (we want these)
- Stack B: Issues opponent values MORE than us (trade material)
- Strategy: Propose from Stack A first, concede from Stack B
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...domain.models import Offer, Allocation, Issue, UtilityFunction, GameSpec
from ...agent_api.context import AgentContext


class StackStrategy(Enum):
    """Strategy for building and using stacks."""
    AGGRESSIVE = "aggressive"  # Prioritize agent's best issues first
    BALANCED = "balanced"  # Mix of agent and opponent preferences
    COOPERATIVE = "cooperative"  # Consider opponent's needs more


@dataclass
class IssueAnalysis:
    """Analysis of a single issue for stack building."""
    issue_name: str
    agent_value: float
    opponent_value: float
    quantity: int
    
    @property
    def value_difference(self) -> float:
        """Positive = agent values more, Negative = opponent values more."""
        return self.agent_value - self.opponent_value
    
    @property
    def total_agent_value(self) -> float:
        return self.agent_value * self.quantity
    
    @property
    def total_opponent_value(self) -> float:
        return self.opponent_value * self.quantity


@dataclass
class NegotiationStacks:
    """
    The two stacks used in NegoChat's issue-by-issue strategy.
    
    Stack A: Issues to claim (agent values more)
    Stack B: Issues to trade (opponent values more)
    """
    stack_a: list[str] = field(default_factory=list)  # Issues to claim
    stack_b: list[str] = field(default_factory=list)  # Issues to concede
    neutral: list[str] = field(default_factory=list)  # Equal value
    
    # Track progress
    a_index: int = 0  # Next issue to propose from A
    b_index: int = 0  # Next issue to concede from B


class NegoChatCore:
    """
    Core NegoChat negotiation algorithm.
    
    This implements the "structured" version without NLU:
    - Uses stacks for issue-by-issue negotiation
    - Generates offers based on stack strategy
    - Evaluates incoming offers
    """
    
    def __init__(
        self,
        game: GameSpec,
        agent_utility: UtilityFunction,
        opponent_utility: UtilityFunction,
        strategy: StackStrategy = StackStrategy.BALANCED,
        min_acceptable_utility: float = 0.4,  # 40% of max
        concession_rate: float = 0.1,  # How fast to concede
    ):
        self.game = game
        self.agent_utility = agent_utility
        self.opponent_utility = opponent_utility
        self.strategy = strategy
        self.min_acceptable_utility = min_acceptable_utility
        self.concession_rate = concession_rate
        
        # Build stacks based on utilities
        self.stacks = self._build_stacks()
        
        # Track negotiation state
        self._current_proposal: Optional[Offer] = None
        self._last_opponent_offer: Optional[Offer] = None
        self._concession_count = 0
        self._offers_made = 0
    
    def _build_stacks(self) -> NegotiationStacks:
        """
        Build Stack A and Stack B based on value differences.
        
        Stack A: Issues where agent_value > opponent_value
        Stack B: Issues where opponent_value > agent_value
        """
        analyses = []
        
        for issue in self.game.issues:
            agent_val = self.agent_utility.values.get(issue.name, 0)
            opp_val = self.opponent_utility.values.get(issue.name, 0)
            
            analyses.append(IssueAnalysis(
                issue_name=issue.name,
                agent_value=agent_val,
                opponent_value=opp_val,
                quantity=issue.quantity,
            ))
        
        # Sort by value difference
        analyses.sort(key=lambda a: a.value_difference, reverse=True)
        
        stacks = NegotiationStacks()
        
        for analysis in analyses:
            if analysis.value_difference > 0:
                stacks.stack_a.append(analysis.issue_name)
            elif analysis.value_difference < 0:
                stacks.stack_b.append(analysis.issue_name)
            else:
                stacks.neutral.append(analysis.issue_name)
        
        # Order within stacks based on strategy
        if self.strategy == StackStrategy.AGGRESSIVE:
            # Most valuable to agent first
            stacks.stack_a.sort(
                key=lambda n: self.agent_utility.values.get(n, 0), 
                reverse=True
            )
            stacks.stack_b.sort(
                key=lambda n: self.agent_utility.values.get(n, 0), 
                reverse=True
            )
        elif self.strategy == StackStrategy.COOPERATIVE:
            # Issues opponent values less first (easier trades)
            stacks.stack_b.sort(
                key=lambda n: self.opponent_utility.values.get(n, 0)
            )
        
        return stacks
    
    def get_opening_offer(self) -> Offer:
        """
        Generate the opening offer.
        
        Strategy: Claim all of Stack A, split neutral, offer Stack B.
        """
        offer = Offer()
        
        for issue in self.game.issues:
            if issue.name in self.stacks.stack_a:
                # We want these - start by claiming all
                offer[issue.name] = Allocation.all_to_agent(issue.quantity)
            elif issue.name in self.stacks.stack_b:
                # They want these - offer some to show good faith
                if self.strategy == StackStrategy.COOPERATIVE:
                    offer[issue.name] = Allocation.all_to_human(issue.quantity)
                else:
                    offer[issue.name] = Allocation.split_even(issue.quantity)
            else:
                # Neutral - split
                offer[issue.name] = Allocation.split_even(issue.quantity)
        
        self._current_proposal = offer
        self._offers_made += 1
        return offer
    
    def get_next_offer(self, ctx: AgentContext) -> Optional[Offer]:
        """
        Generate the next offer based on negotiation progress.
        
        Strategy:
        1. If we haven't proposed yet, give opening offer
        2. If opponent made a counter, evaluate and respond
        3. Otherwise, make a concession from Stack B
        """
        if self._offers_made == 0:
            return self.get_opening_offer()
        
        # Make a concession
        return self._make_concession()
    
    def _make_concession(self) -> Optional[Offer]:
        """
        Make a concession by giving up something from Stack B.
        """
        if self._current_proposal is None:
            return self.get_opening_offer()
        
        offer = self._current_proposal.copy()
        made_change = False
        
        # Try to concede from Stack B (issues opponent wants)
        for issue_name in self.stacks.stack_b:
            issue = self.game.get_issue(issue_name)
            if issue is None:
                continue
            
            current = offer[issue_name]
            if current is None:
                continue
            
            # If we still have some, give one to opponent
            if current.agent > 0:
                offer[issue_name] = Allocation(
                    agent=current.agent - 1,
                    middle=current.middle,
                    human=current.human + 1,
                )
                made_change = True
                break
            elif current.middle > 0:
                offer[issue_name] = Allocation(
                    agent=current.agent,
                    middle=current.middle - 1,
                    human=current.human + 1,
                )
                made_change = True
                break
        
        # If couldn't concede from B, try neutral issues
        if not made_change:
            for issue_name in self.stacks.neutral:
                issue = self.game.get_issue(issue_name)
                if issue is None:
                    continue
                
                current = offer[issue_name]
                if current is None:
                    continue
                
                if current.agent > 0:
                    offer[issue_name] = Allocation(
                        agent=current.agent - 1,
                        middle=current.middle,
                        human=current.human + 1,
                    )
                    made_change = True
                    break
        
        # Last resort: concede from Stack A
        if not made_change:
            for issue_name in reversed(self.stacks.stack_a):  # Least valuable first
                issue = self.game.get_issue(issue_name)
                if issue is None:
                    continue
                
                current = offer[issue_name]
                if current is None:
                    continue
                
                if current.agent > 0:
                    offer[issue_name] = Allocation(
                        agent=current.agent - 1,
                        middle=current.middle,
                        human=current.human + 1,
                    )
                    made_change = True
                    break
        
        if made_change:
            self._current_proposal = offer
            self._concession_count += 1
            self._offers_made += 1
            return offer
        
        return None  # No more concessions possible
    
    def evaluate_offer(self, offer: Offer, ctx: AgentContext) -> dict:
        """
        Evaluate an incoming offer.
        
        Returns dict with:
        - acceptable: bool
        - utility: float
        - utility_percent: float
        - recommendation: str (accept/reject/counter)
        - issues_analysis: dict per issue
        """
        utility = self.agent_utility.calculate(offer)
        max_utility = self.agent_utility.get_max_possible(self.game.issues)
        utility_percent = (utility / max_utility) if max_utility > 0 else 0
        
        # Analyze each issue
        issues_analysis = {}
        for issue in self.game.issues:
            alloc = offer[issue.name]
            if alloc:
                agent_value = alloc.agent * self.agent_utility.values.get(issue.name, 0)
                issues_analysis[issue.name] = {
                    "agent_gets": alloc.agent,
                    "human_gets": alloc.human,
                    "undecided": alloc.middle,
                    "agent_value": agent_value,
                }
        
        # Determine recommendation
        acceptable = utility_percent >= self.min_acceptable_utility
        
        if acceptable and offer.is_complete():
            recommendation = "accept"
        elif utility_percent >= self.min_acceptable_utility * 0.8:
            recommendation = "counter_mild"  # Small counter
        else:
            recommendation = "counter_strong"  # Need significant change
        
        return {
            "acceptable": acceptable,
            "utility": utility,
            "utility_percent": utility_percent,
            "max_utility": max_utility,
            "recommendation": recommendation,
            "issues_analysis": issues_analysis,
        }
    
    def handle_offer(self, offer: Offer, ctx: AgentContext) -> tuple[str, Optional[Offer]]:
        """
        Handle an incoming offer from opponent.
        
        Returns:
            (action, counter_offer) where action is 'accept', 'reject', or 'counter'
        """
        self._last_opponent_offer = offer
        evaluation = self.evaluate_offer(offer, ctx)
        
        if evaluation["recommendation"] == "accept":
            return ("accept", None)
        
        # Generate counter-offer
        counter = self._generate_counter(offer, evaluation)
        
        if counter is None:
            # Can't generate better counter, consider accepting or rejecting
            if evaluation["utility_percent"] >= self.min_acceptable_utility * 0.9:
                return ("accept", None)
            return ("reject", None)
        
        return ("counter", counter)
    
    def _generate_counter(self, opponent_offer: Offer, evaluation: dict) -> Optional[Offer]:
        """
        Generate a counter-offer to opponent's proposal.
        
        Strategy: Start from opponent's offer and adjust toward our preferences.
        """
        counter = opponent_offer.copy()
        changes_made = 0
        max_changes = 2  # Don't change too much at once
        
        # Try to improve on Stack A issues
        for issue_name in self.stacks.stack_a:
            if changes_made >= max_changes:
                break
            
            issue = self.game.get_issue(issue_name)
            if issue is None:
                continue
            
            alloc = counter[issue_name]
            if alloc is None:
                continue
            
            # If opponent gave themselves some, try to take it back
            if alloc.human > 0 and alloc.agent < issue.quantity:
                counter[issue_name] = Allocation(
                    agent=alloc.agent + 1,
                    middle=alloc.middle,
                    human=alloc.human - 1,
                )
                changes_made += 1
        
        # Offer something from Stack B as compensation
        for issue_name in self.stacks.stack_b:
            if changes_made >= max_changes:
                break
            
            issue = self.game.get_issue(issue_name)
            if issue is None:
                continue
            
            alloc = counter[issue_name]
            if alloc is None:
                continue
            
            # Give opponent more of what they want
            if alloc.agent > 0:
                counter[issue_name] = Allocation(
                    agent=alloc.agent - 1,
                    middle=alloc.middle,
                    human=alloc.human + 1,
                )
                changes_made += 1
        
        if changes_made > 0:
            self._current_proposal = counter
            self._offers_made += 1
            return counter
        
        return None
    
    def reset(self) -> None:
        """Reset for a new negotiation."""
        self.stacks = self._build_stacks()
        self._current_proposal = None
        self._last_opponent_offer = None
        self._concession_count = 0
        self._offers_made = 0
    
    def get_stats(self) -> dict:
        """Get negotiation statistics."""
        return {
            "offers_made": self._offers_made,
            "concessions": self._concession_count,
            "stack_a_size": len(self.stacks.stack_a),
            "stack_b_size": len(self.stacks.stack_b),
            "neutral_size": len(self.stacks.neutral),
        }

