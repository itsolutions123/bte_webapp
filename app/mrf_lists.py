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


# --- MRF forms (migration 022). DECIDED by the user 2026-11-12 (part 42), docs/SCHEMA.md section 7. ---
# Single source of truth for form status values, question types, the fixed classification options
# and the form name limit. Validated in app code, not by database constraints.
MRF_FORM_STATUS_ACTIVE = "ACTIVE"
MRF_FORM_STATUS_DRAFT = "DRAFT"
MRF_FORM_STATUSES = (MRF_FORM_STATUS_ACTIVE, MRF_FORM_STATUS_DRAFT)

# Form Assignment (migration 023, DECIDED part 59, docs/API_CONTRACT.md PATCH /api/v1/admin/mrf/forms/{form_id}).
# A separate MRF-only list, not business_units. Order is the order shown in the Set assignment dropdown.
# Also enforced by the CHECK ck_mrf_forms_assignment on mrf_forms.assignment: keep the two in step.
MRF_ASSIGNMENTS = ("Store Operations", "Head Office", "Commissary", "Cali Beach")

MRF_QUESTION_TYPE_YES_NO = "YES_NO"
MRF_QUESTION_TYPE_MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
MRF_QUESTION_TYPE_OPEN_ENDED = "OPEN_ENDED"
MRF_QUESTION_TYPE_FILE_UPLOAD = "FILE_UPLOAD"
MRF_QUESTION_TYPES = (
    MRF_QUESTION_TYPE_YES_NO,
    MRF_QUESTION_TYPE_MULTIPLE_CHOICE,
    MRF_QUESTION_TYPE_OPEN_ENDED,
    MRF_QUESTION_TYPE_FILE_UPLOAD,
)

# The Classification element in the form builder creates a MULTIPLE_CHOICE question with exactly these options, locked.
# Order is the order shown. Option ids are assigned by the server when the question is created.
MRF_CLASSIFICATION_OPTIONS = ("Rank and File", "Supervisory", "Managerial")

# Trimmed form names are at most this long (decided, option A; longer returns 422). Matches mrf_forms.name VARCHAR(100).
MRF_FORM_NAME_MAX_LENGTH = 100

# Trimmed question text is at most this long (decided, part 50, (z8) option A; longer returns 422). mrf_form_questions.question_text itself is unbounded.
MRF_QUESTION_TEXT_MAX_LENGTH = 500

# MRF request status (migration 024, DECIDED part 64, docs/API_CONTRACT.md).
# A new request starts Pending; HR sets Approved or Rejected once (a decision is final).
# Also enforced by the CHECK ck_mrf_requests_status on mrf_requests.status: keep the two in step.
MRF_REQUEST_STATUS_PENDING = "Pending"
MRF_REQUEST_STATUS_APPROVED = "Approved"
MRF_REQUEST_STATUS_REJECTED = "Rejected"
MRF_REQUEST_STATUSES = (
    MRF_REQUEST_STATUS_PENDING,
    MRF_REQUEST_STATUS_APPROVED,
    MRF_REQUEST_STATUS_REJECTED,
)

# Trimmed OPEN_ENDED answers on a submitted MRF request are at most this long (DECIDED part 65 sign-off (b), option A;
# longer returns 422 "Answers must be 1000 characters or fewer."). mrf_request_answers.answer itself is unbounded Text.
MRF_ANSWER_MAX_LENGTH = 1000

# FILE_UPLOAD attachments (docs/API_CONTRACT.md, POST /api/v1/mrf/requests, f6 to f9). The storage path is the
# default for the MRF_ATTACHMENT_STORAGE_PATH env var; it is separate from the resume storage.
MRF_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
MRF_ATTACHMENT_CHUNK_BYTES = 8192
MRF_ATTACHMENT_DEFAULT_STORAGE_PATH = "/data/mrf_attachments"
