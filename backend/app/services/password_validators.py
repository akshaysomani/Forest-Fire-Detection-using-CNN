import re
from app.core.exceptions import ValidationException


def validate_password_strength(password: str) -> None:
    """Validates that a password meets complexity requirements.

    Requirements:
    - Minimum length of 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one numeric digit
    - At least one special character (@$!%*?&_#)
    """
    if len(password) < 8:
        raise ValidationException("Password must be at least 8 characters long.")

    if not re.search(r"[A-Z]", password):
        raise ValidationException("Password must contain at least one uppercase letter.")

    if not re.search(r"[a-z]", password):
        raise ValidationException("Password must contain at least one lowercase letter.")

    if not re.search(r"\d", password):
        raise ValidationException("Password must contain at least one number.")

    if not re.search(r"[@$!%*?&_#]", password):
        raise ValidationException("Password must contain at least one special character (@$!%*?&_#).")
