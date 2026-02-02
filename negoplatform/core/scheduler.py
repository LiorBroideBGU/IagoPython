"""
Scheduler for time-based events.

Handles:
- TIME tick events (every 5 seconds by default)
- Deadline monitoring
- Delayed action execution coordination
"""

import threading
import time
from typing import Callable, Optional
from dataclasses import dataclass

from .events import Event, EventType
from .bus import EventBus


@dataclass
class ScheduledAction:
    """A scheduled action to be executed at a specific time."""
    execute_at: float
    action: Callable[[], None]
    action_id: str
    repeat_interval: Optional[float] = None  # For repeating actions


class Scheduler:
    """
    Manages time-based events for the negotiation.
    
    Responsibilities:
    - Emit TIME events at regular intervals
    - Track negotiation deadline
    - Allow scheduling of delayed actions
    """
    
    def __init__(
        self, 
        event_bus: EventBus,
        time_tick_interval_ms: int = 5000,
        deadline_seconds: Optional[int] = None,
    ):
        self._event_bus = event_bus
        self._tick_interval = time_tick_interval_ms / 1000.0  # Convert to seconds
        self._deadline = deadline_seconds
        
        self._start_time: Optional[float] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Scheduled actions
        self._actions: list[ScheduledAction] = []
        self._actions_lock = threading.Lock()
        
        # Callbacks
        self._on_timeout: Optional[Callable[[], None]] = None
        self._on_tick: Optional[Callable[[float, Optional[float]], None]] = None
    
    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._start_time = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
    
    def reset(self) -> None:
        """Reset the scheduler for a new negotiation."""
        self._start_time = time.time()
        with self._actions_lock:
            self._actions.clear()
    
    def set_deadline(self, seconds: Optional[int]) -> None:
        """Set or update the deadline."""
        self._deadline = seconds
    
    def set_on_timeout(self, callback: Callable[[], None]) -> None:
        """Set callback for when deadline is reached."""
        self._on_timeout = callback
    
    def set_on_tick(self, callback: Callable[[float, Optional[float]], None]) -> None:
        """Set callback for each time tick (elapsed, remaining)."""
        self._on_tick = callback
    
    def get_elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
    
    def get_remaining(self) -> Optional[float]:
        """Get remaining time in seconds, or None if no deadline."""
        if self._deadline is None:
            return None
        return max(0, self._deadline - self.get_elapsed())
    
    def is_timed_out(self) -> bool:
        """Check if deadline has been exceeded."""
        remaining = self.get_remaining()
        return remaining is not None and remaining <= 0
    
    def schedule_action(
        self, 
        delay_ms: int, 
        action: Callable[[], None],
        action_id: Optional[str] = None,
    ) -> str:
        """
        Schedule an action to be executed after a delay.
        
        Returns the action ID.
        """
        action_id = action_id or f"action_{time.time()}"
        execute_at = time.time() + (delay_ms / 1000.0)
        
        scheduled = ScheduledAction(
            execute_at=execute_at,
            action=action,
            action_id=action_id,
        )
        
        with self._actions_lock:
            self._actions.append(scheduled)
            self._actions.sort(key=lambda a: a.execute_at)
        
        return action_id
    
    def cancel_action(self, action_id: str) -> bool:
        """Cancel a scheduled action. Returns True if found and cancelled."""
        with self._actions_lock:
            original_len = len(self._actions)
            self._actions = [a for a in self._actions if a.action_id != action_id]
            return len(self._actions) < original_len
    
    def cancel_all_actions(self) -> int:
        """Cancel all scheduled actions. Returns count cancelled."""
        with self._actions_lock:
            count = len(self._actions)
            self._actions.clear()
            return count
    
    def _run_loop(self) -> None:
        """Main scheduler loop."""
        last_tick = time.time()
        
        while self._running:
            now = time.time()
            
            # Process scheduled actions
            self._process_actions(now)
            
            # Check for time tick
            if now - last_tick >= self._tick_interval:
                self._emit_time_tick()
                last_tick = now
            
            # Check for timeout
            if self.is_timed_out():
                self._handle_timeout()
                break
            
            # Small sleep to avoid busy-waiting
            time.sleep(0.05)
    
    def _process_actions(self, now: float) -> None:
        """Execute any actions that are due."""
        actions_to_run = []
        
        with self._actions_lock:
            # Find actions that are due
            while self._actions and self._actions[0].execute_at <= now:
                actions_to_run.append(self._actions.pop(0))
        
        # Execute outside the lock
        for action in actions_to_run:
            try:
                action.action()
            except Exception as e:
                print(f"Error executing scheduled action {action.action_id}: {e}")
    
    def _emit_time_tick(self) -> None:
        """Emit a TIME event."""
        elapsed = self.get_elapsed()
        remaining = self.get_remaining()
        
        # Publish TIME event
        event = Event.time_tick(elapsed, remaining)
        self._event_bus.publish(event)
        
        # Call tick callback if set
        if self._on_tick:
            try:
                self._on_tick(elapsed, remaining)
            except Exception as e:
                print(f"Error in tick callback: {e}")
    
    def _handle_timeout(self) -> None:
        """Handle deadline timeout."""
        self._running = False
        
        # Publish game end event
        event = Event.game_end("timeout")
        self._event_bus.publish(event)
        
        # Call timeout callback if set
        if self._on_timeout:
            try:
                self._on_timeout()
            except Exception as e:
                print(f"Error in timeout callback: {e}")


class TypingIndicator:
    """
    Manages "typing..." indicator timing.
    
    Shows indicator when agent is processing, hides when they respond.
    Mirrors IAGO's OFFER_IN_PROGRESS indicator behavior.
    """
    
    def __init__(self, event_bus: EventBus, sender_id: str = "agent"):
        self._event_bus = event_bus
        self._sender_id = sender_id
        self._is_showing = False
        self._hide_timer: Optional[threading.Timer] = None
    
    def show(self, auto_hide_ms: Optional[int] = None) -> None:
        """Show the typing indicator."""
        if self._is_showing:
            return
        
        self._is_showing = True
        event = Event.offer_in_progress(self._sender_id)
        self._event_bus.publish(event)
        
        if auto_hide_ms:
            self._schedule_hide(auto_hide_ms)
    
    def hide(self) -> None:
        """Hide the typing indicator."""
        if self._hide_timer:
            self._hide_timer.cancel()
            self._hide_timer = None
        
        self._is_showing = False
        # The indicator is automatically hidden when agent sends next action
    
    def _schedule_hide(self, delay_ms: int) -> None:
        """Schedule automatic hide."""
        if self._hide_timer:
            self._hide_timer.cancel()
        
        self._hide_timer = threading.Timer(delay_ms / 1000.0, self.hide)
        self._hide_timer.daemon = True
        self._hide_timer.start()
    
    @property
    def is_showing(self) -> bool:
        return self._is_showing

