from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


LiveCallback = Optional[Callable[[Dict[str, Any]], None]]


@dataclass
class AskRequest:
    question: str
    preferred_dataset_ids: Optional[List[int]] = None
    allowed_dataset_ids: Optional[List[int]] = None
    live_callback: LiveCallback = None
    model_id: Optional[int] = None
    session_id: str = ""
    conversation_history: Optional[List[Dict[str, Any]]] = None
    current_user: Optional[Dict[str, Any]] = None
    requested_flow: str = ""


@dataclass
class ConfirmRequest:
    session_id: str
    selected_option: str
    selected_dataset_ids: Optional[List[int]] = None
    allowed_dataset_ids: Optional[List[int]] = None
    option_id: str = ""
    live_callback: LiveCallback = None
    current_user: Optional[Dict[str, Any]] = None
    requested_flow: str = ""


@dataclass
class FlowDecision:
    flow: str
    reason: str
    requested_flow: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flow": self.flow,
            "reason": self.reason,
            "requested_flow": self.requested_flow,
        }
