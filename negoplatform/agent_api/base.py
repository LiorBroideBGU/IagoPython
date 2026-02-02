"""
Base class for negotiation agents.

Defines the interface that all agents must implement.
Follows IAGO's event-driven pattern where agents react to events.
"""

from abc import ABC, abstractmethod
from typing import Optional

from .actions import Action
from .context import AgentContext
from ..core.events import Event, EventType


class NegotiationAgent(ABC):
    """
    Abstract base class for negotiation agents.
    
    Agents respond to events by returning a list of Actions.
    Each event type has a corresponding handler method.
    
    Example implementation:
    
        class MyAgent(NegotiationAgent):
            def on_send_offer(self, ctx, event):
                if ctx.get_agent_utility_percent() > 50:
                    return [FormalAccept()]
                return [SendMessage("I need a better deal")]
    """
    
    def __init__(self, agent_id: str = "agent"):
        self.agent_id = agent_id
        self._config: dict = {}
    
    def configure(self, config: dict) -> None:
        """
        Configure the agent with parameters.
        
        Override this to handle custom configuration.
        """
        self._config = config
    
    def get_config(self, key: str, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)
    
    # Main dispatch method
    
    def handle_event(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Main entry point for handling events.
        
        Dispatches to the appropriate handler based on event type.
        Override specific on_* methods, not this one.
        """
        handlers = {
            EventType.SEND_MESSAGE: self.on_send_message,
            EventType.SEND_OFFER: self.on_send_offer,
            EventType.SEND_EXPRESSION: self.on_send_expression,
            EventType.OFFER_IN_PROGRESS: self.on_offer_in_progress,
            EventType.TIME: self.on_time,
            EventType.FORMAL_ACCEPT: self.on_formal_accept,
            EventType.GAME_START: self.on_game_start,
            EventType.GAME_END: self.on_game_end,
        }
        
        handler = handlers.get(event.event_type)
        if handler:
            result = handler(ctx, event)
            return result if result else []
        
        return []
    
    # Event handlers - override these in subclasses
    
    def on_send_message(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle SEND_MESSAGE event (human sent a chat message).
        
        The message text is in event.get_text().
        Preference data (if any) is in event.get_preference().
        """
        return []
    
    def on_send_offer(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle SEND_OFFER event (human proposed an offer).
        
        The offer dict is in event.get_offer().
        This is where most negotiation logic happens.
        """
        return []
    
    def on_send_expression(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle SEND_EXPRESSION event (human sent an emotion).
        
        The expression is in event.get_expression().
        Often agents mirror or respond to emotions.
        """
        return []
    
    def on_offer_in_progress(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle OFFER_IN_PROGRESS event (human is editing offer).
        
        Can be used to pause agent actions while human is working.
        """
        return []
    
    def on_time(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle TIME event (periodic time tick).
        
        payload contains 'elapsed_seconds' and optionally 'remaining_seconds'.
        Use this for timeout-based behaviors or to prompt idle humans.
        """
        return []
    
    def on_formal_accept(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle FORMAL_ACCEPT event (human formally accepted).
        
        If agent also accepts, negotiation ends successfully.
        Agent can accept or propose a different offer.
        """
        return []
    
    def on_game_start(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle GAME_START event (negotiation beginning).
        
        Good place for greeting message or opening offer.
        """
        return []
    
    def on_game_end(self, ctx: AgentContext, event: Event) -> list[Action]:
        """
        Handle GAME_END event (negotiation ending).
        
        payload contains 'reason' and optionally 'final_offer'.
        Use for cleanup or final messages.
        """
        return []
    
    # Utility methods for subclasses
    
    def get_name(self) -> str:
        """Get the agent's display name."""
        return self._config.get("name", "Agent")
    
    def get_avatar(self) -> Optional[str]:
        """Get the agent's avatar identifier."""
        return self._config.get("avatar", "default")
    
    def get_description(self) -> str:
        """Get a description of this agent."""
        return "A negotiation agent"
    
    def reset(self) -> None:
        """
        Reset agent state for a new negotiation.
        
        Override this if your agent maintains state across events.
        """
        pass


class SimpleAgent(NegotiationAgent):
    """
    A minimal agent that accepts any offer above a threshold.
    
    Useful as a baseline or for testing.
    """
    
    def __init__(
        self, 
        agent_id: str = "simple_agent",
        min_utility_percent: float = 40.0,
        greeting: str = "Hello! Let's negotiate.",
    ):
        super().__init__(agent_id)
        self.min_utility_percent = min_utility_percent
        self.greeting = greeting
    
    def on_game_start(self, ctx: AgentContext, event: Event) -> list[Action]:
        from .actions import SendMessage, SendExpression
        from ..core.events import Expression, MessageSubtype
        
        return [
            SendExpression(Expression.HAPPY, duration_ms=1500),
            SendMessage(self.greeting, subtype=MessageSubtype.GREETING),
        ]
    
    def on_send_offer(self, ctx: AgentContext, event: Event) -> list[Action]:
        from .actions import SendMessage, FormalAccept
        from ..core.events import MessageSubtype
        
        utility_pct = ctx.get_agent_utility_percent()
        
        if utility_pct >= self.min_utility_percent:
            if ctx.can_formally_accept():
                return [
                    SendMessage("That works for me!", subtype=MessageSubtype.OFFER_ACCEPT),
                    FormalAccept(),
                ]
            else:
                return [
                    SendMessage("I like this direction, but let's finalize all items.", 
                               subtype=MessageSubtype.OFFER_ACCEPT),
                ]
        else:
            return [
                SendMessage("I'll need a better deal than that.", 
                           subtype=MessageSubtype.OFFER_REJECT),
            ]
    
    def on_send_expression(self, ctx: AgentContext, event: Event) -> list[Action]:
        from .actions import SendExpression
        from ..core.events import Expression
        
        # Mirror the expression
        expr_str = event.get_expression()
        try:
            expr = Expression(expr_str)
            return [SendExpression(expr, duration_ms=1500)]
        except ValueError:
            return []
    
    def get_description(self) -> str:
        return f"Simple agent that accepts offers with >{self.min_utility_percent}% utility"

