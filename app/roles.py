"""Single source of truth for user role names (Rule 13: no second copy of the role list).
Imported by the role checks in app/main.py and the users endpoints. seed_admin.py still has its own
VALID_ROLES copy until it is switched to this module (separate step)."""

ROLE_SUPERADMIN = "SUPERADMIN"
ROLE_MANAGER = "MANAGER"
ROLE_RECRUITER = "RECRUITER"

ALL_ROLES = frozenset({ROLE_SUPERADMIN, ROLE_MANAGER, ROLE_RECRUITER})
