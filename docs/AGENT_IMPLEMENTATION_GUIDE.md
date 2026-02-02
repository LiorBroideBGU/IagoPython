# Agent Implementation Guide

This guide explains how to implement a custom negotiation agent for the NegoChat platform.

## Overview

The negotiation platform uses an **event-driven architecture** where agents respond to events (human messages, offers, emotions, etc.) by returning a list of actions. This design follows the IAGO negotiation system pattern.

```
┌─────────────┐      Event       ┌─────────────┐
│   Human     │  ──────────────▶ │   Agent     │
│   (GUI)     │                  │  (Your Code)│
│             │  ◀──────────────  │             │
└─────────────┘     Actions      └─────────────┘
```

## Quick Start

### 1. Create Your Agent Class

Create a new Python file in `negoplatform/plugins/` (e.g., `my_agent.py`):

```python
from negoplatform.agent_api.base import NegotiationAgent
from negoplatform.agent_api.actions import (
    SendMessage, SendOffer, SendExpression, FormalAccept
)
from negoplatform.agent_api.context import AgentContext
from negoplatform.core.events import Event, Expression, MessageSubtype


class MyAgent(NegotiationAgent):
    """A custom negotiation agent."""
    
    def __init__(self, agent_id: str = "my_agent"):
        super().__init__(agent_id)
        self._min_utility_percent = 50.0
    
    def on_game_start(self, ctx: AgentContext, event: Event) -> list:
        return [
            SendExpression(Expression.HAPPY, duration_ms=1500),
            SendMessage("Hello! Let's make a deal.", subtype=MessageSubtype.GREETING),
        ]
    
    def on_send_offer(self, ctx: AgentContext, event: Event) -> list:
        utility = ctx.get_agent_utility_percent()
        
        if utility >= self._min_utility_percent:
            if ctx.can_formally_accept():
                return [
                    SendMessage("Deal!", subtype=MessageSubtype.OFFER_ACCEPT),
                    FormalAccept(),
                ]
            return [SendMessage("I like this direction!")]
        
        return [SendMessage("I need a better offer.", subtype=MessageSubtype.OFFER_REJECT)]
    
    def get_description(self) -> str:
        return "My custom negotiation agent"
```

### 2. Run Your Agent

The plugin system will automatically discover your agent. Start the platform:

```bash
python -m negoplatform.main
```

---

## Core Concepts

### Event Handlers

Your agent responds to events by overriding handler methods. Each handler receives:
- `ctx: AgentContext` — Read-only access to the current negotiation state
- `event: Event` — The event that triggered this handler

| Handler Method | Triggered When | Common Use |
|----------------|----------------|------------|
| `on_game_start(ctx, event)` | Negotiation begins | Send greeting, opening offer |
| `on_send_offer(ctx, event)` | Human proposes an offer | Accept, reject, or counter-offer |
| `on_send_message(ctx, event)` | Human sends a chat message | Respond to questions, statements |
| `on_send_expression(ctx, event)` | Human sends an emotion | Mirror or respond emotionally |
| `on_formal_accept(ctx, event)` | Human formally accepts current offer | Accept or propose alternative |
| `on_time(ctx, event)` | Periodic time tick | Prompt idle users, time-based behavior |
| `on_offer_in_progress(ctx, event)` | Human is editing an offer | Pause actions while they work |
| `on_game_end(ctx, event)` | Negotiation ends | Cleanup, final message |

### Actions

Handlers return a `list[Action]` to specify what the agent should do:

| Action | Description | Example |
|--------|-------------|---------|
| `SendMessage(text, subtype)` | Send a chat message | `SendMessage("I agree!", subtype=MessageSubtype.OFFER_ACCEPT)` |
| `SendOffer(offer)` | Propose an offer allocation | `SendOffer(counter_offer)` |
| `SendExpression(expr, duration_ms)` | Display an emotion | `SendExpression(Expression.HAPPY, 2000)` |
| `FormalAccept()` | Accept current offer (ends negotiation) | `FormalAccept()` |
| `FormalReject(reason)` | Reject and end negotiation | `FormalReject("No acceptable offer")` |
| `ShowTyping()` | Show "typing..." indicator | `ShowTyping()` |
| `Schedule(delay_ms, action)` | Execute an action after a delay | `Schedule(1000, SendMessage("..."))` |

#### Message Subtypes

Use `MessageSubtype` to categorize messages (useful for logging and analysis):

```python
from negoplatform.core.events import MessageSubtype

# Offer-related
MessageSubtype.OFFER_PROPOSE    # Proposing an offer
MessageSubtype.OFFER_ACCEPT     # Accepting an offer
MessageSubtype.OFFER_REJECT     # Rejecting an offer

# Preference-related
MessageSubtype.PREF_INFO        # Sharing preference info
MessageSubtype.PREF_REQUEST     # Asking about preferences

# Social
MessageSubtype.GREETING         # Hello, welcome
MessageSubtype.FAREWELL         # Goodbye
MessageSubtype.THANKS           # Thank you
MessageSubtype.APOLOGY          # Sorry

MessageSubtype.GENERIC          # Default/unspecified
```

#### Expressions (Emotions)

Available emotional expressions:

```python
from negoplatform.core.events import Expression

Expression.NEUTRAL    # Default state
Expression.HAPPY      # Positive, agreeable
Expression.SAD        # Disappointed
Expression.ANGRY      # Frustrated, upset
Expression.SURPRISED  # Unexpected
Expression.DISGUSTED  # Strong negative (agent-only)
Expression.SCARED     # Anxious (agent-only)
Expression.CONTEMPT   # Dismissive (agent-only)
```

---

## The AgentContext

The `AgentContext` provides everything your agent needs to make decisions without being able to modify the session state directly.

### Utility Calculations

```python
# Get agent's utility for the current offer (as percentage of maximum)
utility_pct = ctx.get_agent_utility_percent()

# Get opponent's utility
opponent_utility = ctx.get_opponent_utility_percent()

# Check if offer meets a minimum threshold
if ctx.is_offer_acceptable(min_utility_percent=40.0):
    # Offer is acceptable
    pass

# Calculate utility for a specific offer
my_utility = ctx.get_agent_utility(some_offer)
```

### Current State

```python
# The current offer on the table
current = ctx.current_offer

# Can we formally accept? (True if offer is complete - no items in middle)
if ctx.can_formally_accept():
    return [FormalAccept()]

# Is the current offer complete?
ctx.is_offer_complete()
```

### Game Information

```python
# List of all issues (negotiable items)
for issue in ctx.issues:
    print(f"{issue.name}: {issue.quantity} items")

# Get issue names
names = ctx.issue_names  # ['apples', 'oranges', 'bananas']

# Get a specific issue
apples = ctx.get_issue('apples')
```

### Preference Analysis

```python
# Get agent's issues sorted by preference (most valuable first)
priorities = ctx.get_agent_preference_order()  # ['apples', 'oranges', 'bananas']

# Get the agent's most/least valued issue
best = ctx.get_agent_best_issue()   # 'apples'
worst = ctx.get_agent_worst_issue()  # 'bananas'

# Same for opponent
opp_priorities = ctx.get_opponent_preference_order()
```

### History

```python
# Get the last offer made by the human
last_human_offer = ctx.get_last_human_offer()

# Get the last offer made by the agent
last_agent_offer = ctx.get_last_agent_offer()

# Count total offers exchanged
total_offers = ctx.get_offer_count()
human_offers = ctx.get_human_offer_count()
agent_offers = ctx.get_agent_offer_count()

# Time since last action (for detecting idle users)
idle_time = ctx.get_time_since_last_action()
```

### Timing

```python
# How long has the negotiation been running?
elapsed = ctx.elapsed_seconds

# Time remaining (if deadline exists)
if ctx.remaining_seconds is not None:
    print(f"{ctx.remaining_seconds} seconds left")
```

---

## Working with Offers

### The Offer Model

An `Offer` contains allocations for each issue. Each issue has a 3-row allocation:
- **Agent row**: Items going to the agent
- **Middle row**: Undecided items
- **Human row**: Items going to the human

```python
from negoplatform.domain.models import Offer, Allocation

# Create an offer
offer = Offer()

# Allocate 3 apples to agent, 0 in middle, 2 to human
offer['apples'] = Allocation(agent=3, middle=0, human=2)

# Helper methods for common allocations
offer['oranges'] = Allocation.all_to_agent(4)     # All 4 to agent
offer['bananas'] = Allocation.all_to_human(3)     # All 3 to human
offer['lemons'] = Allocation.split_even(6)        # 3 agent, 0 middle, 3 human
offer['limes'] = Allocation.all_in_middle(4)      # All undecided
```

### Creating Counter-Offers

```python
def on_send_offer(self, ctx: AgentContext, event: Event) -> list:
    # Create a counter-offer based on preferences
    counter = Offer()
    
    # Give agent their best issue, give human their best issue
    agent_best = ctx.get_agent_best_issue()
    human_best = ctx.get_opponent_preference_order()[0]
    
    for issue in ctx.issues:
        if issue.name == agent_best:
            counter[issue.name] = Allocation.all_to_agent(issue.quantity)
        elif issue.name == human_best:
            counter[issue.name] = Allocation.all_to_human(issue.quantity)
        else:
            counter[issue.name] = Allocation.split_even(issue.quantity)
    
    return [
        SendMessage("How about this?", subtype=MessageSubtype.OFFER_PROPOSE),
        SendOffer(counter),
    ]
```

---

## Complete Example Agent

Here's a full-featured agent implementation:

```python
"""
Balanced Agent - Aims for fair deals while protecting minimum utility.
"""

from negoplatform.agent_api.base import NegotiationAgent
from negoplatform.agent_api.actions import (
    SendMessage, SendOffer, SendExpression, FormalAccept, Schedule
)
from negoplatform.agent_api.context import AgentContext
from negoplatform.core.events import Event, Expression, MessageSubtype
from negoplatform.domain.models import Offer, Allocation


class BalancedAgent(NegotiationAgent):
    """
    A balanced negotiation agent that:
    - Greets warmly at start
    - Accepts offers above minimum utility threshold
    - Makes fair counter-offers when rejecting
    - Mirrors human emotions
    - Prompts idle users
    """
    
    def __init__(self, agent_id: str = "balanced_agent"):
        super().__init__(agent_id)
        self._min_utility_percent = 45.0
        self._idle_threshold_seconds = 30.0
        self._has_prompted = False
    
    def configure(self, config: dict) -> None:
        """Load configuration parameters."""
        super().configure(config)
        behavior = config.get("behavior", {})
        self._min_utility_percent = behavior.get("min_acceptable_utility", 0.45) * 100
        self._idle_threshold_seconds = behavior.get("idle_prompt_seconds", 30.0)
    
    def reset(self) -> None:
        """Reset state for a new negotiation."""
        self._has_prompted = False
    
    # --- Event Handlers ---
    
    def on_game_start(self, ctx: AgentContext, event: Event) -> list:
        """Send a friendly greeting when negotiation starts."""
        return [
            SendExpression(Expression.HAPPY, duration_ms=2000),
            SendMessage(
                "Hello! I'm looking forward to finding a deal that works for both of us.",
                subtype=MessageSubtype.GREETING
            ),
        ]
    
    def on_send_offer(self, ctx: AgentContext, event: Event) -> list:
        """Evaluate human's offer and respond appropriately."""
        utility = ctx.get_agent_utility_percent()
        
        # Good offer - accept it
        if utility >= self._min_utility_percent:
            if ctx.can_formally_accept():
                return [
                    SendExpression(Expression.HAPPY, duration_ms=2000),
                    SendMessage("That's a fair deal. I accept!", subtype=MessageSubtype.OFFER_ACCEPT),
                    FormalAccept(),
                ]
            return [
                SendMessage(
                    "I like where this is going! Let's finalize the remaining items.",
                    subtype=MessageSubtype.OFFER_ACCEPT
                ),
            ]
        
        # Poor offer - counter with something fair
        return self._make_counter_offer(ctx)
    
    def on_send_message(self, ctx: AgentContext, event: Event) -> list:
        """Respond to human messages."""
        text = event.get_text() or ""
        
        # Simple responses based on content
        if "?" in text:
            # It's a question - acknowledge
            return [
                SendMessage(
                    "Good question! Let's focus on finding a fair split.",
                    subtype=MessageSubtype.GENERIC
                ),
            ]
        
        return []  # No response to general statements
    
    def on_send_expression(self, ctx: AgentContext, event: Event) -> list:
        """Mirror human emotions (with some variation)."""
        expr_str = event.get_expression()
        
        try:
            human_expr = Expression(expr_str)
            
            # Mirror positive, soften negative
            if human_expr == Expression.HAPPY:
                return [SendExpression(Expression.HAPPY, duration_ms=1500)]
            elif human_expr == Expression.ANGRY:
                return [
                    SendExpression(Expression.SAD, duration_ms=1500),
                    SendMessage("I understand your frustration. Let's work together.", 
                               subtype=MessageSubtype.APOLOGY),
                ]
            elif human_expr == Expression.SAD:
                return [SendExpression(Expression.NEUTRAL, duration_ms=1500)]
            
        except ValueError:
            pass
        
        return []
    
    def on_formal_accept(self, ctx: AgentContext, event: Event) -> list:
        """Human wants to finalize - check if we agree."""
        if ctx.can_formally_accept():
            utility = ctx.get_agent_utility_percent()
            
            # Accept if above a lower threshold (they initiated)
            if utility >= self._min_utility_percent * 0.9:
                return [
                    SendExpression(Expression.HAPPY, duration_ms=2000),
                    SendMessage("Deal! Pleasure doing business with you.", 
                               subtype=MessageSubtype.OFFER_ACCEPT),
                    FormalAccept(),
                ]
        
        return [
            SendMessage(
                "I appreciate the offer, but I'd like to adjust a few things first.",
                subtype=MessageSubtype.OFFER_REJECT
            ),
        ]
    
    def on_time(self, ctx: AgentContext, event: Event) -> list:
        """Prompt idle users."""
        idle_time = ctx.get_time_since_last_action()
        
        if idle_time and idle_time > self._idle_threshold_seconds and not self._has_prompted:
            self._has_prompted = True
            return [
                SendMessage(
                    "Take your time! Let me know if you have any questions about the items.",
                    subtype=MessageSubtype.GENERIC
                ),
            ]
        
        return []
    
    def on_game_end(self, ctx: AgentContext, event: Event) -> list:
        """Say goodbye when negotiation ends."""
        reason = event.payload.get("reason", "")
        
        if reason == "mutual_accept":
            return [SendMessage("Thanks for the negotiation!", subtype=MessageSubtype.FAREWELL)]
        
        return [SendMessage("Until next time!", subtype=MessageSubtype.FAREWELL)]
    
    # --- Helper Methods ---
    
    def _make_counter_offer(self, ctx: AgentContext) -> list:
        """Create a fair counter-offer."""
        counter = Offer()
        
        agent_priorities = ctx.get_agent_preference_order()
        human_priorities = ctx.get_opponent_preference_order()
        
        for issue in ctx.issues:
            # Agent gets their top priority
            if issue.name == agent_priorities[0]:
                counter[issue.name] = Allocation.all_to_agent(issue.quantity)
            # Human gets their top priority (if different)
            elif issue.name == human_priorities[0]:
                counter[issue.name] = Allocation.all_to_human(issue.quantity)
            # Split the rest
            else:
                counter[issue.name] = Allocation.split_even(issue.quantity)
        
        return [
            SendExpression(Expression.NEUTRAL, duration_ms=1000),
            SendMessage(
                "How about we each take what we value most?",
                subtype=MessageSubtype.OFFER_PROPOSE
            ),
            SendOffer(counter),
        ]
    
    def get_description(self) -> str:
        return f"Balanced agent accepting offers above {self._min_utility_percent}% utility"
```

---

## Deployment Options

### Option 1: Plugin System (Recommended)

1. Save your agent to `negoplatform/plugins/your_agent.py`
2. The plugin loader auto-discovers classes extending `NegotiationAgent`
3. Reference it in configuration by filename (without `.py`)

### Option 2: JSON Configuration

Create a config file referencing your agent:

```json
{
  "agent_type": "your_agent",
  "name": "Your Agent Name",
  "avatar": "default",
  "behavior": {
    "min_acceptable_utility": 0.45,
    "response_delay_ms": 1000,
    "idle_prompt_seconds": 30
  },
  "personality": {
    "emotional_mirroring": true,
    "initial_greeting": "Hello! Let's negotiate."
  }
}
```

### Option 3: Direct Integration

For tighter integration, you can instantiate agents directly:

```python
from negoplatform.plugins.your_agent import YourAgent

agent = YourAgent()
agent.configure({"name": "Custom Name"})
```

---

## File Reference

| File | Description |
|------|-------------|
| `agent_api/base.py` | `NegotiationAgent` base class - extend this |
| `agent_api/actions.py` | All action types your agent can return |
| `agent_api/context.py` | `AgentContext` - read-only state access |
| `core/events.py` | Event types, expressions, message subtypes |
| `domain/models.py` | `Offer`, `Allocation`, `Issue`, `GameSpec` |
| `plugins/example_agent.py` | Complete working example |
| `plugins/plugin_loader.py` | Plugin discovery and loading |

---

## Tips & Best Practices

1. **Start simple** - Begin with `on_game_start` and `on_send_offer`, add complexity gradually

2. **Use subtypes** - Always specify `MessageSubtype` for better logging and analysis

3. **Check `can_formally_accept()`** - Only call `FormalAccept()` when the offer is complete

4. **Mirror emotions** - Responding to expressions makes the agent feel more human

5. **Handle idle time** - Use `on_time` to prompt inactive users

6. **Test utility calculations** - Make sure your thresholds work with the game's utility values

7. **Chain actions with delays** - Use `Schedule` or the `chain_actions()` helper for natural pacing:
   ```python
   from negoplatform.agent_api.actions import chain_actions
   
   actions = chain_actions(
       ShowTyping(),
       SendMessage("Let me think..."),
       SendOffer(counter),
       SendExpression(Expression.HAPPY),
       gap_ms=800
   )
   ```

---

## See Also

- `plugins/example_agent.py` - A complete working example
- `agents/negochat/` - The full NegoChat agent implementation
- `config/agent_config.json` - Default agent configuration

