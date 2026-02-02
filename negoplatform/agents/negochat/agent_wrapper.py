"""
NegoChat Agent Wrapper.

Implements the NegotiationAgent interface using NegoChat's core algorithm.
"""

from typing import Optional

from ...agent_api.base import NegotiationAgent
from ...agent_api.actions import (
    Action, SendMessage, SendOffer, SendExpression, 
    Schedule, FormalAccept, ShowTyping, chain_actions
)
from ...agent_api.context import AgentContext
from ...core.events import Event, EventType, MessageSubtype, Expression
from ...domain.models import Offer

from .negochat_core import NegoChatCore, StackStrategy
from .templates import NegoChatTemplates


class NegoChatAgent(NegotiationAgent):
    """
    NegoChat negotiation agent.
    
    Implements issue-by-issue negotiation using the NegoChat algorithm.
    This is the "structured" version without NLU - uses offer builder
    for structured offers and templates for responses.
    """
    
    def __init__(
        self,
        agent_id: str = "negochat",
        strategy: StackStrategy = StackStrategy.BALANCED,
        min_acceptable_utility: float = 0.4,
        concession_rate: float = 0.1,
        emotional_mirroring: bool = True,
        response_delay_ms: int = 1000,
        idle_prompt_seconds: float = 30.0,
    ):
        super().__init__(agent_id)
        
        self.strategy = strategy
        self.min_acceptable_utility = min_acceptable_utility
        self.concession_rate = concession_rate
        self.emotional_mirroring = emotional_mirroring
        self.response_delay_ms = response_delay_ms
        self.idle_prompt_seconds = idle_prompt_seconds
        
        # These are set when game starts
        self._core: Optional[NegoChatCore] = None
        self._templates: Optional[NegoChatTemplates] = None
        self._last_action_time: float = 0
        self._greeting_sent: bool = False
        self._time_ticks_since_action: int = 0
        self._consecutive_bad_offers: int = 0
    
    def configure(self, config: dict) -> None:
        """Configure agent from dict."""
        super().configure(config)
        
        self.strategy = StackStrategy(config.get("strategy", self.strategy.value))
        self.min_acceptable_utility = config.get("min_acceptable_utility", self.min_acceptable_utility)
        self.concession_rate = config.get("concession_rate", self.concession_rate)
        self.emotional_mirroring = config.get("emotional_mirroring", self.emotional_mirroring)
        self.response_delay_ms = config.get("response_delay_ms", self.response_delay_ms)
        self.idle_prompt_seconds = config.get("idle_prompt_seconds", self.idle_prompt_seconds)
    
    def _initialize_core(self, ctx: AgentContext) -> None:
        """Initialize the core algorithm with game context."""
        self._core = NegoChatCore(
            game=ctx.game,
            agent_utility=ctx.agent_utility,
            opponent_utility=ctx.opponent_utility,
            strategy=self.strategy,
            min_acceptable_utility=self.min_acceptable_utility,
            concession_rate=self.concession_rate,
        )
        self._templates = NegoChatTemplates(ctx.game)
    
    def on_game_start(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle game start - send greeting and optionally opening offer."""
        self._initialize_core(ctx)
        self._greeting_sent = False
        self._time_ticks_since_action = 0
        
        actions = []
        
        # Greeting with smile
        actions.append(SendExpression(Expression.HAPPY, duration_ms=1500))
        actions.append(SendMessage(
            self._templates.get_greeting(),
            subtype=MessageSubtype.GREETING,
            delay_ms=500,
        ))
        
        # Opening offer
        opening = self._core.get_opening_offer()
        actions.append(SendMessage(
            f"{self._templates.get_opening_proposal()} {self._templates.describe_offer(opening)}",
            subtype=MessageSubtype.OFFER_PROPOSE,
            delay_ms=self.response_delay_ms,
        ))
        actions.append(SendOffer(opening, delay_ms=300))
        
        self._greeting_sent = True
        self._time_ticks_since_action = 0
        
        return actions
    
    def on_send_offer(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle incoming offer from human."""
        if self._core is None:
            self._initialize_core(ctx)
        
        self._time_ticks_since_action = 0
        
        # Parse the incoming offer
        offer_dict = event.get_offer()
        if not offer_dict:
            return []
        
        offer = Offer.from_dict(offer_dict)
        
        # Check for unfairness/stubbornness
        utility_pct = ctx.get_agent_utility_percent(offer)
        
        # Definition of "unfair": < 20% utility or Human takes > 80% of items
        is_unfair = utility_pct < 20.0
        
        if is_unfair:
            self._consecutive_bad_offers += 1
        else:
            self._consecutive_bad_offers = 0
            
        # Trigger anger if unfair OR repeated bad offers
        should_be_angry = is_unfair or self._consecutive_bad_offers >= 2
        
        # Evaluate and respond
        action, counter = self._core.handle_offer(offer, ctx)
        
        actions = []
        
        if action == "accept":
            # Accept the offer
            if offer.is_complete():
                actions.append(SendExpression(Expression.HAPPY, duration_ms=2000))
                actions.append(SendMessage(
                    self._templates.get_accept_text(is_complete=True),
                    subtype=MessageSubtype.OFFER_ACCEPT,
                    delay_ms=self.response_delay_ms,
                ))
                actions.append(FormalAccept(delay_ms=500))
            else:
                actions.append(SendMessage(
                    self._templates.get_accept_text(is_complete=False),
                    subtype=MessageSubtype.OFFER_ACCEPT,
                    delay_ms=self.response_delay_ms,
                ))
        
        elif action == "counter" and counter:
            # Counter-offer
            evaluation = self._core.evaluate_offer(offer, ctx)
            is_strong_reject = evaluation["utility_percent"] < self.min_acceptable_utility * 0.5
            
            # Use ANGRY if unfair/stubborn, otherwise SAD for strong reject
            if should_be_angry:
                actions.append(SendExpression(Expression.ANGRY, duration_ms=2500))
            elif is_strong_reject:
                actions.append(SendExpression(Expression.SAD, duration_ms=1500))
            
            # If angry, send a specific message about unfairness if possible, or standard reject
            reject_text = self._templates.get_reject_text(strong=True)
            if should_be_angry:
                reject_text = "That is simply not fair. I cannot accept that."

            actions.append(SendMessage(
                reject_text if should_be_angry else self._templates.get_reject_text(strong=is_strong_reject),
                subtype=MessageSubtype.OFFER_REJECT,
                delay_ms=self.response_delay_ms,
            ))
            actions.append(SendMessage(
                f"{self._templates.get_counter_proposal()} {self._templates.describe_offer(counter)}",
                subtype=MessageSubtype.OFFER_PROPOSE,
                delay_ms=self.response_delay_ms,
            ))
            actions.append(SendOffer(counter, delay_ms=300))
        
        else:
            # Reject without counter
            # Use ANGRY if unfair/stubborn
            if should_be_angry:
                actions.append(SendExpression(Expression.ANGRY, duration_ms=2500))
            else:
                actions.append(SendExpression(Expression.SAD, duration_ms=1500))

            reject_text = self._templates.get_reject_text(strong=True)
            if should_be_angry:
                reject_text = "I'm getting frustrated. You need to be more reasonable."

            actions.append(SendMessage(
                reject_text,
                subtype=MessageSubtype.OFFER_REJECT,
                delay_ms=self.response_delay_ms,
            ))
            
            # Try to make a concession
            concession = self._core._make_concession()
            if concession:
                actions.append(SendMessage(
                    f"{self._templates.get_concession_text()} {self._templates.describe_offer(concession)}",
                    subtype=MessageSubtype.OFFER_PROPOSE,
                    delay_ms=self.response_delay_ms * 2,
                ))
                actions.append(SendOffer(concession, delay_ms=300))
        
        return actions
    
    def on_send_message(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle incoming message from human."""
        self._time_ticks_since_action = 0
        
        # For now, simple acknowledgment
        # A full implementation would parse preferences from the message
        text = event.get_text() or ""
        
        actions = []
        
        # Check for preference expression
        pref = event.get_preference()
        if pref and self._templates:
            if pref.is_query:
                # They're asking about our preferences
                best_issue = ctx.get_agent_best_issue()
                actions.append(SendMessage(
                    self._templates.get_want_issue_text(best_issue),
                    subtype=MessageSubtype.PREF_INFO,
                    delay_ms=self.response_delay_ms,
                ))
            else:
                # They're telling us their preferences - acknowledge
                actions.append(SendMessage(
                    "Good to know, thanks for sharing.",
                    subtype=MessageSubtype.CONFIRMATION,
                    delay_ms=self.response_delay_ms,
                ))
        
        return actions
    
    def on_send_expression(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle emotional expression from human."""
        self._time_ticks_since_action = 0
        
        actions = []
        expr_str = event.get_expression()
        
        if expr_str and self._templates:
            # Respond to emotion with text
            actions.append(SendMessage(
                self._templates.get_emotion_response(expr_str),
                delay_ms=self.response_delay_ms,
            ))
            
            # Mirror emotion if enabled
            if self.emotional_mirroring:
                try:
                    expr = Expression(expr_str)
                    # Mirror or respond appropriately
                    if expr == Expression.ANGRY:
                        actions.append(SendExpression(Expression.NEUTRAL, duration_ms=1500))
                    elif expr == Expression.SAD:
                        actions.append(SendExpression(Expression.SAD, duration_ms=1500))
                    else:
                        actions.append(SendExpression(expr, duration_ms=1500))
                except ValueError:
                    pass
        
        return actions
    
    def on_formal_accept(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle formal accept from human."""
        self._time_ticks_since_action = 0
        
        actions = []
        
        # If offer is acceptable, we also accept
        if ctx.can_formally_accept():
            utility_pct = ctx.get_agent_utility_percent()
            
            if utility_pct >= self.min_acceptable_utility:
                actions.append(SendExpression(Expression.HAPPY, duration_ms=2000))
                actions.append(SendMessage(
                    self._templates.get_accept_text(is_complete=True) if self._templates else "Deal!",
                    subtype=MessageSubtype.OFFER_ACCEPT,
                    delay_ms=self.response_delay_ms,
                ))
                actions.append(FormalAccept(delay_ms=500))
            else:
                # Not good enough for us
                actions.append(SendMessage(
                    "I appreciate you being ready to close, but I need a better deal.",
                    subtype=MessageSubtype.OFFER_REJECT,
                    delay_ms=self.response_delay_ms,
                ))
        
        return actions
    
    def on_time(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle time tick - prompt if idle too long."""
        self._time_ticks_since_action += 1
        
        actions = []
        
        # Check if we should prompt the human
        time_since_action = ctx.get_time_since_last_action()
        if time_since_action and time_since_action > self.idle_prompt_seconds:
            if self._templates:
                # Check remaining time
                if ctx.remaining_seconds and ctx.remaining_seconds < 60:
                    actions.append(SendMessage(
                        self._templates.get_time_pressure_text(),
                        subtype=MessageSubtype.TIMING_INFO,
                    ))
                else:
                    actions.append(SendMessage(
                        self._templates.get_prompt_text(),
                        delay_ms=500,
                    ))
                
                # Reset counter
                self._time_ticks_since_action = 0
        
        return actions
    
    def on_game_end(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle game end."""
        actions = []
        
        reason = event.payload.get("reason", "unknown")
        success = reason == "mutual_agreement"
        
        if self._templates:
            actions.append(SendMessage(
                self._templates.get_farewell(success),
                subtype=MessageSubtype.FAREWELL,
            ))
        
        if success:
            actions.append(SendExpression(Expression.HAPPY, duration_ms=3000))
        else:
            actions.append(SendExpression(Expression.SAD, duration_ms=2000))
        
        return actions
    
    def on_offer_in_progress(self, ctx: AgentContext, event: Event) -> list[Action]:
        """Handle offer in progress (human is editing)."""
        # Reset idle counter when human is active
        self._time_ticks_since_action = 0
        return []
    
    def reset(self) -> None:
        """Reset agent state."""
        if self._core:
            self._core.reset()
        self._greeting_sent = False
        self._time_ticks_since_action = 0
        self._consecutive_bad_offers = 0
    
    def get_description(self) -> str:
        return f"NegoChat agent using {self.strategy.value} strategy"

