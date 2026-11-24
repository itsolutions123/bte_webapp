from pydantic import BaseModel, EmailStr, UUID4, Json, StrictBool
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# --- Public Schemas ---
class PublicJob(BaseModel):
    id: UUID4
    slug: str
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    location: Optional[str] = None
    pay_information: Optional[str] = None
    job_type: Optional[str] = None
    brand_id: UUID4
    brand_name: str
    brand_slug: str

class PublicJobsResponse(BaseModel):
    data: List[PublicJob]
    total: int

class PublicJobQuestion(BaseModel):
    id: UUID4
    display_order: int
    question_text: str
    question_type: Optional[str] = None
    options: Optional[Any] = None

class PublicJobQuestionsResponse(BaseModel):
    data: List[PublicJobQuestion]

class ApplicantAnswerItem(BaseModel):
    question_id: UUID4
    answer: str

# --- Admin Schemas ---
class JobCounts(BaseModel):
    NEW: int = 0
    PASSED: int = 0
    FAILED: int = 0
    POOLING: int = 0
    ENDORSED: int = 0
    HIRED: int = 0

class AdminTallyItem(BaseModel):
    job_id: UUID4
    job_title: str
    counts: JobCounts

class AdminTallyResponse(BaseModel):
    data: List[AdminTallyItem]

class AdminApplicationListItem(BaseModel):
    id: UUID4
    applicant_name: str
    job_title: str
    score: Optional[int]
    status: str
    has_hard_fail_flag: bool
    created_at: datetime

class AdminApplicationListResponse(BaseModel):
    data: List[AdminApplicationListItem]
    total: int

class AdminApplicantDetail(BaseModel):
    name: str
    email: str
    phone: Optional[str]
    gender: Optional[str]
    address: Optional[str]
    age: Optional[int]

class AdminAnswerDetail(BaseModel):
    question: str
    question_type: Optional[str]
    applicant_answer: str
    is_passed: Optional[bool]

class AdminDuplicateApplication(BaseModel):
    job_title: str
    status: str
    date: datetime

class AdminApplicationDetailResponse(BaseModel):
    id: UUID4
    applicant: AdminApplicantDetail
    job_title: str
    score: Optional[int]
    status: str
    answers: List[AdminAnswerDetail]

class AdminStatusPatchRequest(BaseModel):
    status: str


class FormCreateRequest(BaseModel):
    name: str

class FormResponse(BaseModel):
    id: UUID4
    slug: str
    name: str

class FormArchiveResponse(BaseModel):
    id: UUID4
    slug: str
    name: str
    archived_at: datetime

class FormListItem(BaseModel):
    id: UUID4
    slug: str
    name: str
    job_count: int
    archived_at: Optional[datetime] = None

class FormListResponse(BaseModel):
    data: List[FormListItem]
    total: int


class BrandCreateRequest(BaseModel):
    name: str
    business_unit_id: UUID4

class BrandResponse(BaseModel):
    id: UUID4
    name: str
    slug: str

class BrandRenameRequest(BaseModel):
    name: str

class BusinessUnitCreateRequest(BaseModel):
    name: str

class BusinessUnitResponse(BaseModel):
    id: UUID4
    name: str
    slug: str

class BrandArchiveResponse(BaseModel):
    id: UUID4
    slug: str
    name: str
    archived_at: datetime
    jobs_archived: int

class JobCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    location: Optional[str] = None
    pay_information: Optional[str] = None
    job_type: Optional[str] = None
    employee_classification: Optional[str] = None
    is_active: bool = False

class JobUpdateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    location: Optional[str] = None
    pay_information: Optional[str] = None
    job_type: Optional[str] = None
    employee_classification: Optional[str] = None
    is_active: bool

class JobResponse(BaseModel):
    id: UUID4
    brand_id: UUID4
    title: str
    slug: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    is_active: bool
    form_id: Optional[UUID4] = None
    location: Optional[str] = None
    pay_information: Optional[str] = None
    job_type: Optional[str] = None
    employee_classification: Optional[str] = None
    created_at: datetime
    archived_at: Optional[datetime] = None

class BrandJobItem(BaseModel):
    id: UUID4
    title: str
    is_active: bool
    created_at: Optional[datetime] = None
    form_name: Optional[str] = None

class BrandJobsResponse(BaseModel):
    data: List[BrandJobItem]
    total: int

class SidebarBrandItem(BaseModel):
    id: UUID4
    name: str
    slug: str
    slug: str

class SidebarFormItem(BaseModel):
    id: UUID4
    name: str
    slug: str
    slug: str

class SidebarBusinessUnitItem(BaseModel):
    id: UUID4
    name: str
    slug: str
    brands: List[SidebarBrandItem] = []

class SidebarMetadataResponse(BaseModel):
    brands: List[SidebarBrandItem]
    forms: List[SidebarFormItem]
    business_units: List[SidebarBusinessUnitItem] = []

class OverallTotals(BaseModel):
    new: int = 0
    passed: int = 0
    failed: int = 0
    pooling: int = 0
    endorsed: int = 0
    hired: int = 0
    total_processed: int = 0

class BrandSummaryItem(BaseModel):
    brand_id: UUID4
    brand_name: str
    brand_slug: str
    top_matches_count: int = 0

class AdminSummaryResponse(BaseModel):
    overall_totals: OverallTotals
    brand_summaries: List[BrandSummaryItem]


# --- Admin: form questions (docs/API_CONTRACT.md section 3, POST /forms/{form_id}/questions) ---
class QuestionCreateRequest(BaseModel):
    question_type: str
    question_text: str
    options: Optional[List[Any]] = None
    is_hard_requirement: bool = False
    answer_points: Optional[List[Any]] = None
    correct_answer: Optional[Any] = None

class QuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = None
    options: Optional[List[Any]] = None
    is_hard_requirement: Optional[bool] = None
    answer_points: Optional[List[Any]] = None
    correct_answer: Optional[Any] = None

class AnswerPointItem(BaseModel):
    answer_value: str
    target_type: str
    brand_id: Optional[UUID4] = None
    brand_name: Optional[str] = None
    points: int = 1

class QuestionResponse(BaseModel):
    id: UUID4
    display_order: int
    question_type: str
    question_text: str
    options: Optional[List[Any]] = None
    is_hard_requirement: bool = False
    answer_points: List[AnswerPointItem] = []
    correct_answer: Optional[Any] = None


class JobSummaryItem(BaseModel):
    id: UUID4
    slug: str
    title: str
    brand_name: str


class FormDetailResponse(BaseModel):
    id: UUID4
    slug: str
    name: str
    jobs: List[JobSummaryItem] = []
    questions: List[QuestionResponse] = []

# --- Auth Schemas ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    role: str

class MeResponse(BaseModel):
    full_name: Optional[str] = None
    email: str
    role: str


# Rules for new_password are NOT checked here: they run in the handler after the credentials verify.
class ChangePasswordRequest(BaseModel):
    email: EmailStr
    temporary_password: str
    new_password: str


# email is a plain str here: the endpoint trims and lower-cases it before validating (EmailStr would reject padding first).
class UserCreateRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: str


class UserCreateResponse(BaseModel):
    id: UUID4
    first_name: str
    last_name: str
    email: str
    role: str
    temporary_password: str


class UserRoleUpdateRequest(BaseModel):
    role: str


class UserPasswordResetResponse(BaseModel):
    id: UUID4
    temporary_password: str


class UserListItem(BaseModel):
    id: UUID4
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    role: str
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    added_by_name: Optional[str] = None
    archived_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    data: List[UserListItem]
    total: int
    page: int
    limit: int


# MRF portal sign-up (docs/API_CONTRACT.md, POST /api/v1/mrf/signup). Plain str fields on purpose: the endpoint
# trims and lower-cases the email and checks domain, lists, lengths and password rules itself.
class MrfSignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    department: str
    position: str


# MRF portal login (docs/API_CONTRACT.md, POST /api/v1/mrf/login, DECIDED part 37): plain strings, no length caps.
class MrfLoginRequest(BaseModel):
    email: str
    password: str


# MRF admin Users list (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/users). Fields as contracted; never password data.
class MrfUserListItem(BaseModel):
    id: UUID4
    first_name: str
    last_name: str
    email: str
    department: str
    position: str
    status: str


class MrfUserListResponse(BaseModel):
    data: List[MrfUserListItem]
    total: int
    page: int
    page_size: int


class MrfFormListItem(BaseModel):
    id: UUID4
    name: str
    status: str
    question_count: int
    created_at: datetime


class MrfFormListResponse(BaseModel):
    data: List[MrfFormListItem]
    total: int
    page: int
    page_size: int


class MrfPortalFormListItem(BaseModel):
    # GET /api/v1/mrf/forms row (docs/API_CONTRACT.md, part 61): ACTIVE forms only, so no status field.
    id: UUID4
    name: str
    assignment: Optional[str] = None

class MrfPortalFormListResponse(BaseModel):
    data: List[MrfPortalFormListItem]
    total: int
    page: int
    page_size: int

class MrfFormCreate(BaseModel):
    # No length limit here on purpose: the endpoint trims first, then returns its own 422 messages (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/forms).
    name: str


class MrfFormCreated(BaseModel):
    id: UUID4
    name: str
    status: str
    created_at: datetime
    assignment: Optional[str] = None


class MrfFormUpdate(BaseModel):
    # All three fields optional on purpose: the endpoint decides what is usable and returns its own 422 messages (docs/API_CONTRACT.md, PATCH /api/v1/admin/mrf/forms/{form_id}).
    name: Optional[str] = None
    status: Optional[str] = None
    assignment: Optional[str] = None


class MrfFormQuestionCreate(BaseModel):
    # Loose on purpose: the endpoint trims, checks and returns its own 422 messages (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/forms/{form_id}/questions).
    # StrictBool: a non-bool is_required or is_classification gets FastAPI's own list-style 422. is_required None means "use the type's default".
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    is_required: Optional[StrictBool] = None
    is_classification: StrictBool = False
    description: Optional[str] = None


class MrfFormQuestionUpdate(BaseModel):
    # All three fields optional on purpose: the endpoint decides what is usable and returns its own 422 messages (docs/API_CONTRACT.md, PATCH /api/v1/admin/mrf/forms/{form_id}/questions/{question_id})
    # A field sent as null counts as not sent (p3). StrictBool: a non-bool is_required gets FastAPI's own list-style 422.
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    is_required: Optional[StrictBool] = None
    description: Optional[str] = None


class MrfFormQuestionItem(BaseModel):
    id: UUID4
    question_type: str
    question_text: str
    options: Optional[Any] = None
    is_required: bool
    is_classification: bool
    display_order: int
    description: Optional[str] = None


class MrfPortalFormDetail(BaseModel):
    # GET /api/v1/mrf/forms/{form_id} (docs/API_CONTRACT.md, part 68): ACTIVE forms only, so no status field.
    id: UUID4
    name: str
    assignment: Optional[str] = None
    questions: List[MrfFormQuestionItem]


class MrfRequestAnswerIn(BaseModel):
    # One answer in POST /api/v1/mrf/requests (docs/API_CONTRACT.md, part 69). Plain UUID on purpose, not UUID4:
    # a well-formed id that is not on the form must reach the handler and get its own 422 ("Unknown question.").
    # answer is loose: the endpoint trims it, treats blank as not answered and returns its own 422 messages.
    question_id: UUID
    answer: str


class MrfRequestCreate(BaseModel):
    # Plain UUID on purpose: an unknown but well-formed form_id gets the contracted 404, not a list-style 422.
    form_id: UUID
    answers: List[MrfRequestAnswerIn]


class MrfRequestListItem(BaseModel):
    # List-row shape shared by the requestor's request endpoints (docs/API_CONTRACT.md, part 69): the submit 201 and
    # later GET /api/v1/mrf/requests. assignment is NOT NULL on mrf_requests, so never null here.
    id: UUID4
    form_name: str
    assignment: str
    created_at: datetime
    status: str
    remarks: Optional[str] = None


class MrfRequestListResponse(BaseModel):
    data: List[MrfRequestListItem]
    total: int
    page: int
    page_size: int


class MrfAdminRequestListItem(BaseModel):
    # Admin list row (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/requests, part 79). remarks, decided_at, decided_by and decided_by_role are null while Pending (decided_by and decided_by_role: part 82).
    id: UUID4
    submitted_by: str
    classification: str
    department: Optional[str] = None
    assignment: str
    form_name: str
    created_at: datetime
    status: str
    remarks: Optional[str] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
    decided_by_role: Optional[str] = None


class MrfAdminRequestListResponse(BaseModel):
    data: List[MrfAdminRequestListItem]
    total: int
    page: int
    page_size: int


class MrfAdminRequestAnswerItem(BaseModel):
    # One answered question (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/requests/{request_id}, part 80). question_text is the current wording.
    question_id: UUID4
    question_text: str
    question_type: str
    # A FILE_UPLOAD answer has answer null and file_name/file_size set; every other type has both file fields null.
    answer: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None


class MrfAdminRequestDetail(MrfAdminRequestListItem):
    # The list-row fields plus the answered questions in the form display order.
    answers: List[MrfAdminRequestAnswerItem]


class MrfRequestDecision(BaseModel):
    # Loose on purpose: both fields optional so the endpoint returns its own 422 texts (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/requests/{request_id}/decision, part 81).
    # A non-string status or remarks still gets FastAPI's own list-style 422 before the handler runs.
    status: Optional[str] = None
    remarks: Optional[str] = None


class MrfFormDetail(BaseModel):
    id: UUID4
    name: str
    status: str
    created_at: datetime
    assignment: Optional[str] = None
    questions: List[MrfFormQuestionItem]


class MrfQuestionReorder(BaseModel):
    # Plain UUID on purpose, not UUID4: a valid id that is not v4 must reach the id-list check and get the plain-string 422 (r2).
    ordered_ids: List[UUID]


class MrfQuestionReorderResponse(BaseModel):
    questions: List[MrfFormQuestionItem]


class MrfBulkDelete(BaseModel):
    # Plain UUID on purpose, like MrfQuestionReorder. Empty list and cap are checked in the router with plain-string 422 texts.
    ids: List[UUID]


class MrfBulkDeleteSkipped(BaseModel):
    id: UUID
    reason: str


class MrfBulkDeleteResponse(BaseModel):
    deleted: List[UUID]
    skipped: List[MrfBulkDeleteSkipped]
