"""
Offer Builder Widget.

Allows users to construct offers by allocating items between parties.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from dataclasses import dataclass

from ...domain.models import Issue, Offer, Allocation


@dataclass
class IssueAllocation:
    """Tracks allocation for a single issue."""
    issue: Issue
    agent_var: tk.IntVar
    middle_var: tk.IntVar
    human_var: tk.IntVar


class OfferBuilderPanel(ttk.Frame):
    """
    Panel for building negotiation offers.
    
    Features:
    - Per-issue allocation sliders
    - Visual representation of current allocation
    - Send offer button
    - Utility preview
    - Scrollable when many issues
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        on_send_offer: Optional[Callable[[Offer], None]] = None,
        on_offer_changed: Optional[Callable[[Offer], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self._on_send_offer = on_send_offer
        self._on_offer_changed = on_offer_changed
        self._issues: list[Issue] = []
        self._allocations: dict[str, IssueAllocation] = {}
        
        self._create_widgets()
        self._setup_layout()
    
    def _create_widgets(self):
        """Create offer builder widgets."""
        # Title
        self._title_label = ttk.Label(
            self,
            text="Offer Builder",
            font=("Segoe UI", 12, "bold"),
        )
        
        # Scrollable container for issues
        self._scroll_container = ttk.Frame(self)
        
        # Canvas for scrolling
        self._canvas = tk.Canvas(self._scroll_container, highlightthickness=0)
        
        # Scrollbar
        self._scrollbar = ttk.Scrollbar(
            self._scroll_container, 
            orient=tk.VERTICAL, 
            command=self._canvas.yview
        )
        
        # Frame inside canvas that holds the issues
        self._issues_frame = ttk.Frame(self._canvas)
        
        # Create window in canvas
        self._canvas_window = self._canvas.create_window(
            (0, 0), 
            window=self._issues_frame, 
            anchor="nw"
        )
        
        # Configure canvas scrolling
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        
        # Bind events for scrolling
        self._issues_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Bind mouse wheel scrolling
        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)
        
        # Utility preview
        self._utility_frame = ttk.LabelFrame(self, text="Utility Preview")
        self._your_utility_label = ttk.Label(
            self._utility_frame,
            text="Your score: --",
            font=("Segoe UI", 10),
        )
        self._agent_utility_label = ttk.Label(
            self._utility_frame,
            text="Agent score: --",
            font=("Segoe UI", 10),
        )
        
        # Buttons
        self._button_frame = ttk.Frame(self)
        self._send_button = ttk.Button(
            self._button_frame,
            text="Send Offer",
            command=self._send_offer,
        )
        self._reset_button = ttk.Button(
            self._button_frame,
            text="Reset",
            command=self._reset_offer,
        )
    
    def _on_frame_configure(self, event):
        """Update scroll region when frame size changes."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Resize frame to match canvas width."""
        self._canvas.itemconfig(self._canvas_window, width=event.width)
    
    def _bind_mousewheel(self, event):
        """Bind mouse wheel when mouse enters canvas."""
        # Cross-platform mouse wheel binding
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows/macOS
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)    # Linux scroll up
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)    # Linux scroll down
    
    def _unbind_mousewheel(self, event):
        """Unbind mouse wheel when mouse leaves canvas."""
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        # Different handling for different platforms
        if event.num == 4:  # Linux scroll up
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:  # Linux scroll down
            self._canvas.yview_scroll(1, "units")
        else:  # Windows/macOS
            # event.delta is positive for scroll up, negative for scroll down
            # On macOS delta is larger, on Windows it's usually 120/-120
            direction = -1 if event.delta > 0 else 1
            self._canvas.yview_scroll(direction, "units")
    
    def _setup_layout(self):
        """Setup widget layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Make scroll container expandable
        
        # Title
        self._title_label.grid(row=0, column=0, pady=(5, 10), sticky="w")
        
        # Scrollable issues container
        self._scroll_container.grid(row=1, column=0, sticky="nsew", pady=5)
        self._scroll_container.columnconfigure(0, weight=1)
        self._scroll_container.rowconfigure(0, weight=1)
        
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        
        self._issues_frame.columnconfigure(0, weight=1)
        
        # Utility preview
        self._utility_frame.grid(row=2, column=0, sticky="ew", pady=10)
        self._your_utility_label.pack(side=tk.LEFT, padx=10, pady=5)
        self._agent_utility_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Buttons
        self._button_frame.grid(row=3, column=0, sticky="ew", pady=5)
        self._send_button.pack(side=tk.LEFT, padx=5)
        self._reset_button.pack(side=tk.RIGHT, padx=5)
    
    def set_issues(self, issues: list[Issue]):
        """Set the issues to display in the builder."""
        self._issues = issues
        self._allocations.clear()
        
        # Clear existing issue widgets
        for widget in self._issues_frame.winfo_children():
            widget.destroy()
        
        # Create widgets for each issue
        for i, issue in enumerate(issues):
            self._create_issue_row(issue, i)
        
        # Update scroll region
        self._issues_frame.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
    
    def _create_issue_row(self, issue: Issue, row: int):
        """Create allocation controls for a single issue."""
        frame = ttk.LabelFrame(
            self._issues_frame,
            text=f"{issue.display_name} ({issue.quantity} total)",
        )
        frame.grid(row=row, column=0, sticky="ew", pady=5, padx=5)
        frame.columnconfigure(1, weight=1)
        
        # Variables for tracking allocation
        agent_var = tk.IntVar(value=0)
        middle_var = tk.IntVar(value=issue.quantity)
        human_var = tk.IntVar(value=0)
        
        # Store allocation
        self._allocations[issue.name] = IssueAllocation(
            issue=issue,
            agent_var=agent_var,
            middle_var=middle_var,
            human_var=human_var,
        )
        
        # Labels
        ttk.Label(frame, text="Agent", width=8).grid(row=0, column=0, padx=5)
        ttk.Label(frame, text="Undecided", width=10).grid(row=0, column=1)
        ttk.Label(frame, text="You", width=8).grid(row=0, column=2, padx=5)
        
        # Value displays
        agent_label = ttk.Label(frame, textvariable=agent_var, width=3, anchor="center")
        agent_label.grid(row=1, column=0, padx=5)
        
        middle_label = ttk.Label(frame, textvariable=middle_var, width=3, anchor="center")
        middle_label.grid(row=1, column=1)
        
        human_label = ttk.Label(frame, textvariable=human_var, width=3, anchor="center")
        human_label.grid(row=1, column=2, padx=5)
        
        # Slider for human allocation
        slider = ttk.Scale(
            frame,
            from_=0,
            to=issue.quantity,
            orient=tk.HORIZONTAL,
            command=lambda v, name=issue.name: self._on_slider_change(name, v),
        )
        slider.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        
        # Buttons for quick allocation
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=5)
        
        ttk.Button(
            btn_frame,
            text="All to Agent",
            width=12,
            command=lambda name=issue.name: self._set_allocation(name, "agent"),
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="Split",
            width=8,
            command=lambda name=issue.name: self._set_allocation(name, "split"),
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="All to You",
            width=12,
            command=lambda name=issue.name: self._set_allocation(name, "human"),
        ).pack(side=tk.LEFT, padx=2)
    
    def _on_slider_change(self, issue_name: str, value: str):
        """Handle slider value change."""
        alloc = self._allocations.get(issue_name)
        if not alloc:
            return
        
        human_count = int(float(value))
        total = alloc.issue.quantity
        
        # Calculate remaining for agent (middle stays 0 for simplicity)
        agent_count = total - human_count
        
        alloc.human_var.set(human_count)
        alloc.agent_var.set(agent_count)
        alloc.middle_var.set(0)
        
        self._notify_change()
    
    def _set_allocation(self, issue_name: str, mode: str):
        """Set allocation to a preset mode."""
        alloc = self._allocations.get(issue_name)
        if not alloc:
            return
        
        total = alloc.issue.quantity
        
        if mode == "agent":
            alloc.agent_var.set(total)
            alloc.middle_var.set(0)
            alloc.human_var.set(0)
        elif mode == "human":
            alloc.agent_var.set(0)
            alloc.middle_var.set(0)
            alloc.human_var.set(total)
        else:  # split
            half = total // 2
            remainder = total - (half * 2)
            alloc.agent_var.set(half)
            alloc.middle_var.set(remainder)
            alloc.human_var.set(half)
        
        self._notify_change()
    
    def _notify_change(self):
        """Notify that offer has changed."""
        if self._on_offer_changed:
            self._on_offer_changed(self.get_offer())
    
    def get_offer(self) -> Offer:
        """Get the current offer from the builder."""
        offer = Offer()
        
        for name, alloc in self._allocations.items():
            offer[name] = Allocation(
                agent=alloc.agent_var.get(),
                middle=alloc.middle_var.get(),
                human=alloc.human_var.get(),
            )
        
        return offer
    
    def set_offer(self, offer: Offer):
        """Set the builder to display a specific offer."""
        for name, allocation in offer.allocations.items():
            if name in self._allocations and allocation:
                alloc = self._allocations[name]
                alloc.agent_var.set(allocation.agent)
                alloc.middle_var.set(allocation.middle)
                alloc.human_var.set(allocation.human)
    
    def _send_offer(self):
        """Send the current offer."""
        if self._on_send_offer:
            self._on_send_offer(self.get_offer())
    
    def _reset_offer(self):
        """Reset all allocations to middle."""
        for alloc in self._allocations.values():
            alloc.agent_var.set(0)
            alloc.middle_var.set(alloc.issue.quantity)
            alloc.human_var.set(0)
        
        self._notify_change()
    
    def update_utility_preview(self, human_utility: float, agent_utility: float):
        """Update the utility preview display."""
        self._your_utility_label.config(text=f"Your score: {human_utility:.1f}")
        self._agent_utility_label.config(text=f"Agent score: {agent_utility:.1f}")
    
    def set_on_send_offer(self, callback: Callable[[Offer], None]):
        """Set the offer send callback."""
        self._on_send_offer = callback
    
    def set_on_offer_changed(self, callback: Callable[[Offer], None]):
        """Set the offer changed callback."""
        self._on_offer_changed = callback
