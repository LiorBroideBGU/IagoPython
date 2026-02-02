"""
Event Bus for the negotiation platform.

Routes events to subscribers (GUI, agents, loggers) and handles
delayed execution of agent responses.
"""

from collections import defaultdict
from typing import Callable, Optional
from dataclasses import dataclass
import threading
import queue
import time

from .events import Event, EventType


# Type alias for event handlers
EventHandler = Callable[[Event], None]


@dataclass
class Subscription:
    """Represents a subscription to events."""
    handler: EventHandler
    event_types: Optional[set[EventType]]  # None means all types
    subscriber_id: str


class EventBus:
    """
    Central event routing system.
    
    Features:
    - Publish/subscribe pattern
    - Support for delayed event execution
    - Thread-safe operation for GUI integration
    - Event filtering by type
    """
    
    def __init__(self):
        self._subscriptions: list[Subscription] = []
        self._delayed_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._lock = threading.RLock()
        self._running = False
        self._delay_thread: Optional[threading.Thread] = None
        
        # Callback for when delayed events are ready
        self._on_delayed_ready: Optional[Callable[[Event], None]] = None
    
    def subscribe(
        self,
        handler: EventHandler,
        subscriber_id: str,
        event_types: Optional[set[EventType]] = None,
    ) -> None:
        """
        Subscribe to events.
        
        Args:
            handler: Function to call when event occurs
            subscriber_id: Unique identifier for this subscriber
            event_types: Set of event types to listen for, or None for all
        """
        with self._lock:
            # Remove any existing subscription with same ID
            self._subscriptions = [
                s for s in self._subscriptions 
                if s.subscriber_id != subscriber_id
            ]
            self._subscriptions.append(Subscription(
                handler=handler,
                event_types=event_types,
                subscriber_id=subscriber_id,
            ))
    
    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove a subscriber."""
        with self._lock:
            self._subscriptions = [
                s for s in self._subscriptions 
                if s.subscriber_id != subscriber_id
            ]
    
    def publish(self, event: Event) -> None:
        """
        Publish an event to all matching subscribers.
        
        If the event has a delay_ms > 0, it will be queued for
        delayed execution instead of immediate dispatch.
        """
        if event.delay_ms > 0:
            self._queue_delayed(event)
        else:
            self._dispatch(event)
    
    def publish_all(self, events: list[Event]) -> None:
        """Publish multiple events in order."""
        for event in events:
            self.publish(event)
    
    def _dispatch(self, event: Event) -> None:
        """Immediately dispatch event to all matching subscribers."""
        with self._lock:
            subscribers = list(self._subscriptions)
        
        for sub in subscribers:
            if sub.event_types is None or event.event_type in sub.event_types:
                try:
                    sub.handler(event)
                except Exception as e:
                    print(f"Error in event handler {sub.subscriber_id}: {e}")
    
    def _queue_delayed(self, event: Event) -> None:
        """Queue an event for delayed execution."""
        execute_at = time.time() + (event.delay_ms / 1000.0)
        # Priority queue uses (priority, item) tuples
        self._delayed_queue.put((execute_at, event))
    
    def process_delayed_events(self) -> list[Event]:
        """
        Process any delayed events that are ready.
        
        Returns list of events that were dispatched.
        Called by the GUI event loop or scheduler.
        """
        dispatched = []
        now = time.time()
        
        while not self._delayed_queue.empty():
            try:
                # Peek at the next event
                execute_at, event = self._delayed_queue.get_nowait()
                
                if execute_at <= now:
                    # Event is ready, dispatch it
                    self._dispatch(event)
                    dispatched.append(event)
                else:
                    # Not ready yet, put it back
                    self._delayed_queue.put((execute_at, event))
                    break
            except queue.Empty:
                break
        
        return dispatched
    
    def get_next_delay(self) -> Optional[float]:
        """
        Get time until next delayed event (in seconds).
        Returns None if no delayed events.
        """
        try:
            execute_at, event = self._delayed_queue.get_nowait()
            self._delayed_queue.put((execute_at, event))
            return max(0, execute_at - time.time())
        except queue.Empty:
            return None
    
    def has_pending_delayed(self) -> bool:
        """Check if there are delayed events pending."""
        return not self._delayed_queue.empty()
    
    def clear_delayed(self) -> int:
        """Clear all delayed events. Returns count cleared."""
        count = 0
        while not self._delayed_queue.empty():
            try:
                self._delayed_queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        return count
    
    def start_delay_processor(self, on_ready: Callable[[Event], None]) -> None:
        """
        Start background thread for processing delayed events.
        
        Args:
            on_ready: Callback when a delayed event is dispatched
        """
        self._on_delayed_ready = on_ready
        self._running = True
        self._delay_thread = threading.Thread(target=self._delay_loop, daemon=True)
        self._delay_thread.start()
    
    def stop_delay_processor(self) -> None:
        """Stop the background delay processor."""
        self._running = False
        if self._delay_thread:
            self._delay_thread.join(timeout=1.0)
            self._delay_thread = None
    
    def _delay_loop(self) -> None:
        """Background loop for processing delayed events."""
        while self._running:
            events = self.process_delayed_events()
            for event in events:
                if self._on_delayed_ready:
                    try:
                        self._on_delayed_ready(event)
                    except Exception as e:
                        print(f"Error in delayed event callback: {e}")
            
            # Sleep a bit before checking again
            time.sleep(0.05)  # 50ms polling

