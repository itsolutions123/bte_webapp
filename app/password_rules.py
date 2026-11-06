"""Shared new-password rules (docs/API_CONTRACT.md, POST /api/v1/admin/change-password).

Called by a handler AFTER the credentials verify, never from a request schema, so rule
feedback is never given to someone who has not proved they know the temporary password."""
from typing import Optional

PASSWORD_MIN_BYTES = 8
PASSWORD_MAX_BYTES = 72  # bcrypt only reads 72 bytes; longer input is rejected, never truncated


def validate_new_password(new_password: str, temporary_password: str) -> Optional[str]:
    """Return one 422 detail string listing every unmet rule, or None when all rules pass.
    ASSUMPTION, UNCONFIRMED: a special character is any character that is not a letter, number or whitespace."""
    unmet = []

    size = len(new_password.encode("utf-8"))
    if size < PASSWORD_MIN_BYTES or size > PASSWORD_MAX_BYTES:
        unmet.append(f"be {PASSWORD_MIN_BYTES} to {PASSWORD_MAX_BYTES} bytes long")
    if not any(ch.isupper() for ch in new_password):
        unmet.append("include an uppercase letter")
    if not any(ch.islower() for ch in new_password):
        unmet.append("include a lowercase letter")
    if not any(ch.isdigit() for ch in new_password):
        unmet.append("include a number")
    if not any(not (ch.isalnum() or ch.isspace()) for ch in new_password):
        unmet.append("include a special character")
    if new_password == temporary_password:
        unmet.append("be different from the temporary password")

    if not unmet:
        return None
    if len(unmet) == 1:
        joined = unmet[0]
    else:
        joined = ", ".join(unmet[:-1]) + " and " + unmet[-1]
    return f"New password must {joined}."
