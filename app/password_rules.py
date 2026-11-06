"""Shared new-password rules (docs/API_CONTRACT.md, POST /api/v1/admin/change-password).

Called by a handler AFTER the credentials verify, never from a request schema, so rule
feedback is never given to someone who has not proved they know the temporary password."""
from typing import Optional

PASSWORD_MIN_BYTES = 8
PASSWORD_MAX_BYTES = 72  # bcrypt only reads 72 bytes; longer input is rejected, never truncated

# Single shared definition of the rule wording. The 422 message and the /change-password page
# both read these, in this display order (RULE_PHRASES).
RULES_LEAD_IN = "New password must"
RULE_LENGTH = f"be {PASSWORD_MIN_BYTES} to {PASSWORD_MAX_BYTES} bytes long"
RULE_UPPER = "include an uppercase letter"
RULE_LOWER = "include a lowercase letter"
RULE_NUMBER = "include a number"
RULE_SPECIAL = "include a special character"
RULE_DIFFERENT = "be different from the temporary password"
RULE_PHRASES = (
    ("length", RULE_LENGTH),
    ("upper", RULE_UPPER),
    ("lower", RULE_LOWER),
    ("number", RULE_NUMBER),
    ("special", RULE_SPECIAL),
    ("different", RULE_DIFFERENT),
)


def validate_new_password(new_password: str, temporary_password: str) -> Optional[str]:
    """Return one 422 detail string listing every unmet rule, or None when all rules pass.
    ASSUMPTION, UNCONFIRMED: a special character is any character that is not a letter, number or whitespace."""
    unmet = []

    size = len(new_password.encode("utf-8"))
    if size < PASSWORD_MIN_BYTES or size > PASSWORD_MAX_BYTES:
        unmet.append(RULE_LENGTH)
    if not any(ch.isupper() for ch in new_password):
        unmet.append(RULE_UPPER)
    if not any(ch.islower() for ch in new_password):
        unmet.append(RULE_LOWER)
    if not any(ch.isdigit() for ch in new_password):
        unmet.append(RULE_NUMBER)
    if not any(not (ch.isalnum() or ch.isspace()) for ch in new_password):
        unmet.append(RULE_SPECIAL)
    if new_password == temporary_password:
        unmet.append(RULE_DIFFERENT)

    if not unmet:
        return None
    if len(unmet) == 1:
        joined = unmet[0]
    else:
        joined = ", ".join(unmet[:-1]) + " and " + unmet[-1]
    return f"{RULES_LEAD_IN} {joined}."
