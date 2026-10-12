from pydantic import BaseModel, EmailStr, UUID4, Json
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Public Schemas ---
class PublicJob(BaseModel):
    id: UUID4
    slug: str
    title: str
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

class PublicJobQuestionsResponse(BaseModel):
    data: List[PublicJobQuestion]

class ApplicantAnswerItem(BaseModel):
    question_id: UUID4
    answer: str

# --- Admin Schemas ---
class JobCounts(BaseModel):
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

class AdminAnswerDetail(BaseModel):
    question: str
    applicant_answer: str
    is_passed: bool

class AdminDuplicateApplication(BaseModel):
    job_title: str
    status: str
    date: datetime

class AdminApplicationDetailResponse(BaseModel):
    id: UUID4
    applicant: AdminApplicantDetail
    score: Optional[int]
    status: str
    parsed_data: Optional[Dict[str, Any]]
    flags: List[str]
    answers: List[AdminAnswerDetail]
    duplicate_applications: List[AdminDuplicateApplication]

class AdminStatusPatchRequest(BaseModel):
    status: str


class SidebarBrandItem(BaseModel):
    id: UUID4
    name: str
    slug: str
    slug: str
    code: str = "BTE"

class SidebarFormItem(BaseModel):
    id: UUID4
    name: str
    slug: str
    slug: str

class SidebarMetadataResponse(BaseModel):
    brands: List[SidebarBrandItem]
    forms: List[SidebarFormItem]

class OverallTotals(BaseModel):
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
