from pydantic import BaseModel, EmailStr, UUID4, Json
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Public Schemas ---
class PublicJob(BaseModel):
    id: UUID4
    title: str
    brand_id: UUID4
    brand_name: str

class PublicJobsResponse(BaseModel):
    data: List[PublicJob]
    total: int

class PublicJobQuestion(BaseModel):
    id: UUID4
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
