"""Fixed lists for the MRF (Manpower Request Form) portal.

Single source of truth for the sign-up Department and Position options and
for the allowed email domains. Values confirmed by the user and recorded in
docs/SCHEMA.md section 7 (Fixed lists). The sign-up page options are drawn
from these lists, and the sign-up endpoint validates against them
server-side. Do not copy these values anywhere else.
The order of DEPARTMENTS and POSITIONS is the order shown in the dropdowns.
"""

POSITIONS = ("Head", "OIC", "Manager")

DEPARTMENTS = (
    "Accounting",
    "Admin",
    "Audit",
    "BCC",
    "Executive",
    "Human Resources",
    "Marketing",
    "Operations",
    "Procurement",
    "Project Management",
    "Research and Development",
    "Sales",
    "Repairs and Maintenance",
)

# Lowercase, compared against the part of the email after the "@".
ALLOWED_EMAIL_DOMAINS = (
    "bigtimeempire.com",
    "thesandwichguy.com",
    "paresretiro.com",
)
