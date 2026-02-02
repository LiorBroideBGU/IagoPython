"""
Main Application Window.

Integrates all GUI components with the negotiation engine.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from datetime import datetime

from ..domain.models import GameSpec, Offer
from ..core.events import Event, EventType, Expression, HUMAN_ID, AGENT_ID
from ..core.bus import EventBus
from ..core.session import NegotiationSession, SessionState
from ..core.scheduler import Scheduler
from ..agent_api.base import NegotiationAgent
from ..agent_api.context import AgentContext
from ..agent_api.actions import (
    Action, SendMessage, SendOffer, SendExpression, 
    Schedule, FormalAccept, ShowTyping
)

from .widgets.chat import ChatPanel
from .widgets.offer_builder import OfferBuilderPanel
from .widgets.emotion_bar import EmotionBar
from .widgets.status_bar import StatusBar


class NegotiationApp:
    """
    Main application window for the negotiation platform.
    
    Manages:
    - GUI layout and interaction
    - Event routing between GUI, session, and agent
    - Timer updates
    - Action execution
    """
    
    def __init__(
        self,
        game: GameSpec,
        agent: NegotiationAgent,
        title: str = "IAGO Negotiation Platform",
    ):
        self.game = game
        self.agent = agent
        
        # Core components
        self._event_bus = EventBus()
        self._session = NegotiationSession(game)
        self._scheduler: Optional[Scheduler] = None
        
        # Create main window
        self._root = tk.Tk()
        self._root.title(title)
        self._root.geometry("1200x800")
        self._root.minsize(900, 600)
        
        # Apply dark theme
        self._setup_theme()
        
        # Create widgets
        self._create_widgets()
        self._setup_layout()
        
        # Wire up events
        self._setup_event_handlers()
        
        # Timer for periodic updates
        self._timer_id: Optional[str] = None
    
    def _setup_theme(self):
        """Setup dark theme styling."""
        style = ttk.Style()
        
        # Try to use clam theme as base
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        
        # Configure colors
        bg_color = "#1e1e2e"
        fg_color = "#cdd6f4"
        accent_color = "#89b4fa"
        
        style.configure(".", 
            background=bg_color,
            foreground=fg_color,
            fieldbackground=bg_color,
        )
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=accent_color)
        style.configure("TButton", padding=5)
        style.configure("Accent.TButton", foreground="#a6e3a1")
        
        self._root.configure(bg=bg_color)
    
    def _create_widgets(self):
        """Create all application widgets."""
        # Main container
        self._main_frame = ttk.Frame(self._root)
        
        # Status bar (top)
        self._status_bar = StatusBar(
            self._main_frame,
            on_formal_accept=self._on_formal_accept,
        )
        
        # Content area (middle)
        self._content_frame = ttk.Frame(self._main_frame)
        
        # Left panel: Chat
        self._chat_panel = ChatPanel(
            self._content_frame,
            on_send_message=self._on_send_message,
        )
        
        # Right panel: Offer builder
        self._offer_panel = OfferBuilderPanel(
            self._content_frame,
            on_send_offer=self._on_send_offer,
            on_offer_changed=self._on_offer_changed,
        )
        
        # Bottom: Emotion bar
        self._emotion_bar = EmotionBar(
            self._main_frame,
            on_send_expression=self._on_send_expression,
        )
        
        # Initialize offer builder with game issues
        self._offer_panel.set_issues(self.game.issues)
        
        # Set game info in status bar
        self._status_bar.set_game_info(self.game.name, self.game.description)
        self._status_bar.set_deadline(self.game.rules.deadline_seconds)
    
    def _setup_layout(self):
        """Setup widget layout."""
        self._main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar at top
        self._status_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Content area
        self._content_frame.pack(fill=tk.BOTH, expand=True)
        self._content_frame.columnconfigure(0, weight=1)
        self._content_frame.columnconfigure(1, weight=1)
        self._content_frame.rowconfigure(0, weight=1)
        
        self._chat_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._offer_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Emotion bar at bottom
        self._emotion_bar.pack(fill=tk.X, pady=(10, 0))
    
    def _setup_event_handlers(self):
        """Setup event bus subscriptions."""
        # Subscribe to all events for logging/debugging
        self._event_bus.subscribe(
            self._on_event,
            subscriber_id="app",
        )
    
    def _on_event(self, event: Event):
        """Handle all events (for logging)."""
        # Update session state
        self._session.apply_event(event)
        
        # Route to agent if from human
        if event.sender_id == HUMAN_ID:
            self._route_to_agent(event)
        
        # Update UI based on event
        self._update_ui_from_event(event)
    
    def _route_to_agent(self, event: Event):
        """Route an event to the agent and execute responses."""
        # Build agent context
        ctx = self._build_agent_context()
        
        # Get agent's response
        actions = self.agent.handle_event(ctx, event)
        
        # Execute actions
        self._execute_actions(actions)
    
    def _build_agent_context(self) -> AgentContext:
        """Build agent context from current session state."""
        return AgentContext(
            game=self.game,
            agent_utility=self.game.agent_utility,
            opponent_utility=self.game.human_utility,
            current_offer=self._session.current_offer,
            history=self._session.history,
            elapsed_seconds=self._session.get_elapsed_time(),
            remaining_seconds=self._session.get_remaining_time(),
            human_has_accepted=self._session.acceptance.human_accepted,
            agent_has_accepted=self._session.acceptance.agent_accepted,
            session_id=self._session.session_id,
        )
    
    def _execute_actions(self, actions: list[Action]):
        """Execute a list of agent actions."""
        for action in actions:
            if isinstance(action, Schedule):
                # Schedule for later
                self._root.after(action.delay_ms, lambda a=action.action: self._execute_single_action(a))
            elif hasattr(action, 'delay_ms') and action.delay_ms > 0:
                # Action has its own delay
                self._root.after(action.delay_ms, lambda a=action: self._execute_single_action(a))
            else:
                self._execute_single_action(action)
    
    def _execute_single_action(self, action: Action):
        """Execute a single agent action."""
        if isinstance(action, SendMessage):
            # Create and publish message event
            event = Event.send_message(
                sender_id=AGENT_ID,
                text=action.text,
                subtype=action.subtype,
            )
            self._event_bus.publish(event)
            
            # Update chat
            self._chat_panel.add_message("agent", action.text)
        
        elif isinstance(action, SendOffer):
            # Create and publish offer event
            event = Event.send_offer(
                sender_id=AGENT_ID,
                offer_dict=action.offer.to_dict(),
            )
            self._event_bus.publish(event)
            
            # Update offer builder to show agent's offer
            self._offer_panel.set_offer(action.offer)
            self._chat_panel.add_message("system", "Agent sent a new offer.")
            
            # Update utility preview
            self._update_utility_display()
        
        elif isinstance(action, SendExpression):
            # Create and publish expression event
            event = Event.send_expression(
                sender_id=AGENT_ID,
                expression=action.expression,
                duration_ms=action.duration_ms,
            )
            self._event_bus.publish(event)
            
            # Update emotion display
            self._emotion_bar.set_agent_emotion(action.expression, action.duration_ms)
        
        elif isinstance(action, FormalAccept):
            # Create and publish formal accept event
            event = Event.formal_accept(sender_id=AGENT_ID)
            self._event_bus.publish(event)
            
            # Update status
            self._check_negotiation_complete()
        
        elif isinstance(action, ShowTyping):
            self._chat_panel.show_typing_indicator("agent")
    
    def _update_ui_from_event(self, event: Event):
        """Update UI based on an event."""
        # Update status bar
        self._status_bar.update_time(
            self._session.get_elapsed_time(),
            self._session.get_remaining_time(),
        )
        
        # Update acceptance status
        self._status_bar.set_acceptance_status(
            human_accepted=self._session.acceptance.human_accepted,
            agent_accepted=self._session.acceptance.agent_accepted,
            can_accept=self._session.can_formally_accept(),
        )
        
        # Update scores
        self._update_utility_display()
    
    def _update_utility_display(self):
        """Update utility displays."""
        offer = self._offer_panel.get_offer()
        human_util = self.game.human_utility.calculate(offer)
        agent_util = self.game.agent_utility.calculate(offer)
        
        self._offer_panel.update_utility_preview(human_util, agent_util)
        self._status_bar.update_scores(human_util, agent_util)
    
    # Event handlers from GUI
    
    def _on_send_message(self, text: str):
        """Handle user sending a message."""
        event = Event.send_message(sender_id=HUMAN_ID, text=text)
        self._chat_panel.add_message("human", text)
        self._event_bus.publish(event)
    
    def _on_send_offer(self, offer: Offer):
        """Handle user sending an offer."""
        # Validate offer
        is_valid, error = self.game.validate_offer(offer)
        if not is_valid:
            messagebox.showerror("Invalid Offer", error)
            return
        
        event = Event.send_offer(sender_id=HUMAN_ID, offer_dict=offer.to_dict())
        self._chat_panel.add_message("system", "You sent an offer.")
        self._event_bus.publish(event)
    
    def _on_offer_changed(self, offer: Offer):
        """Handle user modifying offer (in progress)."""
        # Emit offer in progress event
        event = Event.offer_in_progress(HUMAN_ID, offer.to_dict())
        self._event_bus.publish(event)
        
        # Update utility preview
        self._update_utility_display()
    
    def _on_send_expression(self, expression: Expression):
        """Handle user sending an expression."""
        event = Event.send_expression(sender_id=HUMAN_ID, expression=expression)
        self._chat_panel.add_message("system", f"You expressed: {expression.value}")
        self._event_bus.publish(event)
    
    def _on_formal_accept(self):
        """Handle user clicking formal accept."""
        if not self._session.can_formally_accept():
            messagebox.showwarning(
                "Cannot Accept",
                "Please ensure all items are allocated before accepting."
            )
            return
        
        event = Event.formal_accept(sender_id=HUMAN_ID)
        self._chat_panel.add_message("system", "You formally accepted the deal.")
        self._event_bus.publish(event)
        
        self._check_negotiation_complete()
    
    def _check_negotiation_complete(self):
        """Check if negotiation is complete and show result."""
        if self._session.acceptance.both_accepted():
            human_util = self._session.get_human_utility()
            agent_util = self._session.get_agent_utility()
            
            messagebox.showinfo(
                "Negotiation Complete!",
                f"Deal reached!\n\n"
                f"Your score: {human_util:.1f}\n"
                f"Agent score: {agent_util:.1f}"
            )
    
    def _start_timer_updates(self):
        """Start periodic timer updates."""
        def update():
            if self._session.is_active:
                self._status_bar.update_time(
                    self._session.get_elapsed_time(),
                    self._session.get_remaining_time(),
                )
                
                # Check for timeout
                if self._session.is_timed_out():
                    self._handle_timeout()
                else:
                    self._timer_id = self._root.after(1000, update)
        
        update()
    
    def _handle_timeout(self):
        """Handle negotiation timeout."""
        event = Event.game_end("timeout")
        self._event_bus.publish(event)
        
        messagebox.showwarning(
            "Time's Up!",
            "The negotiation deadline has passed without an agreement."
        )
    
    def start(self):
        """Start the negotiation and run the application."""
        # Start the session
        start_event = self._session.start()
        self._event_bus.publish(start_event)
        
        # Trigger agent's game start response
        ctx = self._build_agent_context()
        actions = self.agent.on_game_start(ctx, start_event)
        self._execute_actions(actions)
        
        # Update status
        self._status_bar.set_game_status("In progress")
        self._chat_panel.add_message("system", "Negotiation started!")
        
        # Start timer updates
        self._start_timer_updates()
        
        # Focus chat input
        self._chat_panel.focus_input()
        
        # Run main loop
        self._root.mainloop()
    
    def stop(self):
        """Stop the application."""
        if self._timer_id:
            self._root.after_cancel(self._timer_id)
        self._root.quit()


def run_negotiation(
    game: GameSpec,
    agent: NegotiationAgent,
    title: str = "IAGO Negotiation Platform",
):
    """
    Convenience function to run a negotiation.
    
    Args:
        game: The game specification
        agent: The negotiation agent
        title: Window title
    """
    app = NegotiationApp(game, agent, title)
    app.start()

