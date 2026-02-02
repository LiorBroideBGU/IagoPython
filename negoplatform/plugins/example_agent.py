"""
Example Plugin Agent.

Demonstrates how to create a custom agent plugin.
"""

from negoplatform.agent_api.base import NegotiationAgent
from negoplatform.agent_api.actions import (
    Action, SendMessage, SendOffer, SendExpression, FormalAccept
)
from negoplatform.agent_api.context import AgentContext
from negoplatform.core.events import Event, Expression, MessageSubtype
from negoplatform.domain.models import Offer, Allocation


class ExamplePluginAgent(NegotiationAgent):
    """
    A simple example plugin agent.
    
    This agent demonstrates the plugin system by implementing
    basic negotiation behavior:
    - Greets on game start
    - Accepts offers above 50% utility
    - Makes counter-offers by splitting items
    - Mirrors emotions
    """
    
    def __init__(self, agent_id: str = "example_plugin"):
        super().__init__(agent_id)
        self._min_utility_percent = 50.0
    
    def configure(self, config: dict) -> None:
        super().configure(config)
        behavior = config.get("behavior", {})
        self._min_utility_percent = behavior.get("min_acceptable_utility", 0.5) * 100
    
    def on_game_start(self, ctx: AgentContext, event: Event) -> list[Action]:
        # Create opening offer: split evenly (give extra to human for odd quantities)
        opening = Offer()
        for issue in ctx.issues:
            half = issue.quantity // 2
            remainder = issue.quantity - (half * 2)
            # Give remainder to human instead of middle
            opening[issue.name] = Allocation(
                agent=half, 
                middle=0, 
                human=half + remainder
            )
        
        return [
            SendExpression(Expression.HAPPY, duration_ms=1500),
            SendMessage(
                "Hello from the Example Plugin Agent! Let's make a deal.",
                subtype=MessageSubtype.GREETING,
            ),
            SendMessage(
                "How about we split things evenly to start?",
                subtype=MessageSubtype.OFFER_PROPOSE,
            ),
            SendOffer(opening),
        ]
    
    def on_send_offer(self, ctx: AgentContext, event: Event) -> list[Action]:
        utility_pct = ctx.get_agent_utility_percent()
        
        if utility_pct >= self._min_utility_percent:
            if ctx.can_formally_accept():
                return [
                    SendExpression(Expression.HAPPY, duration_ms=2000),
                    SendMessage("That's a deal!", subtype=MessageSubtype.OFFER_ACCEPT),
                    FormalAccept(),
                ]
            return [
                SendMessage(
                    "I like it! Let's finalize the remaining items.",
                    subtype=MessageSubtype.OFFER_ACCEPT,
                )
            ]
        
        # Make counter-offer: split everything (give extra to agent for odd quantities)
        counter = Offer()
        for issue in ctx.issues:
            half = issue.quantity // 2
            remainder = issue.quantity - (half * 2)
            # Give remainder to agent (we're the agent making the counter)
            counter[issue.name] = Allocation(
                agent=half + remainder, 
                middle=0, 
                human=half
            )
        
        return [
            SendMessage(
                "How about we split everything evenly?",
                subtype=MessageSubtype.OFFER_PROPOSE,
            ),
            SendOffer(counter),
        ]
    
    def on_send_expression(self, ctx: AgentContext, event: Event) -> list[Action]:
        expr_str = event.get_expression()
        if expr_str:
            try:
                expr = Expression(expr_str)
                return [SendExpression(expr, duration_ms=1500)]
            except ValueError:
                pass
        return []
    
    def on_formal_accept(self, ctx: AgentContext, event: Event) -> list[Action]:
        if ctx.can_formally_accept():
            utility_pct = ctx.get_agent_utility_percent()
            if utility_pct >= self._min_utility_percent * 0.8:
                return [
                    SendMessage("Deal!", subtype=MessageSubtype.OFFER_ACCEPT),
                    FormalAccept(),
                ]
        return [
            SendMessage(
                "I need a better offer before I can accept.",
                subtype=MessageSubtype.OFFER_REJECT,
            )
        ]
    
    def get_description(self) -> str:
        return "Example plugin agent that accepts offers above 50% utility"

