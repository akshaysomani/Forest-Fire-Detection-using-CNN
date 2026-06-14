from typing import Set, Dict
from app.core.exceptions import ValidationException


class StateManager:
    STATES = {"Draft", "Training", "Validation", "Approved", "Staging", "Production", "Deprecated", "Archived"}

    # Map from state to valid destination states
    VALID_TRANSITIONS: Dict[str, Set[str]] = {
        "Draft": {"Training", "Validation", "Archived"},
        "Training": {"Validation", "Draft", "Archived"},
        "Validation": {"Approved", "Draft", "Archived"},
        "Approved": {"Staging", "Production", "Deprecated", "Archived"},
        "Staging": {"Production", "Approved", "Deprecated", "Archived"},
        "Production": {"Deprecated", "Archived"},
        "Deprecated": {"Archived"},
        "Archived": set(),  # Terminal state
    }

    @classmethod
    def validate_transition(cls, from_state: str, to_state: str) -> None:
        """
        Validates whether a transition between two lifecycle states is allowed.
        Raises ValidationException if invalid.
        """
        f_state = from_state.strip().capitalize()
        t_state = to_state.strip().capitalize()

        if f_state not in cls.STATES:
            raise ValidationException(f"Invalid from_state: '{from_state}'")
        if t_state not in cls.STATES:
            raise ValidationException(f"Invalid to_state: '{to_state}'")

        # Allow no-op transition (self-transition)
        if f_state == t_state:
            return

        valid_destinations = cls.VALID_TRANSITIONS.get(f_state, set())
        if t_state not in valid_destinations:
            raise ValidationException(
                f"Invalid lifecycle transition: '{f_state}' to '{t_state}'. "
                f"Valid destinations from '{f_state}' are: {list(valid_destinations)}"
            )


state_manager = StateManager()
