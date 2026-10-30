import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, DateTime, Date, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Brand(Base):
    __tablename__ = "brands"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    
    jobs = relationship("Job", back_populates="brand")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    slug = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    pass_threshold = Column(Integer, nullable=True)
    pooling_threshold = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    form_id = Column(UUID(as_uuid=True), ForeignKey("forms.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, default=lambda: utc_now() + timedelta(days=30))
    archived_at = Column(DateTime(timezone=True), nullable=True)
    location = Column(String, nullable=True)
    pay_information = Column(String, nullable=True)
    job_type = Column(String, nullable=True)
    
    brand = relationship("Brand", back_populates="jobs")
    questions = relationship("JobQuestion", back_populates="job")
    applications = relationship("Application", back_populates="job")

class Form(Base):
    __tablename__ = "forms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    archived_at = Column(DateTime(timezone=True), nullable=True)

class Applicant(Base):
    __tablename__ = "applicants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    address = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)

    applications = relationship("Application", back_populates="applicant")

    __table_args__ = (
        Index('idx_applicant_email', 'email', unique=True),
    )

class Parameter(Base):
    __tablename__ = "parameters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    job_questions = relationship("JobQuestion", back_populates="parameter")

class JobQuestion(Base):
    __tablename__ = "job_questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    parameter_id = Column(UUID(as_uuid=True), ForeignKey("parameters.id"), nullable=True)
    form_id = Column(UUID(as_uuid=True), ForeignKey("forms.id"), nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    question_type = Column(String, nullable=True)
    question_text = Column(String, nullable=False)
    options = Column(JSONB(none_as_null=True), nullable=True)
    expected_answer = Column(String, nullable=True)
    is_hard_requirement = Column(Boolean, default=False)

    job = relationship("Job", back_populates="questions")
    parameter = relationship("Parameter", back_populates="job_questions")

class Application(Base):
    __tablename__ = "applications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    terms_version = Column(String, nullable=False, default="v1.0")
    consent_agreed = Column(Boolean, nullable=False, default=True)
    resume_path = Column(String, nullable=False)
    resume_filename = Column(String, nullable=False)
    resume_size_bytes = Column(Integer, nullable=False)
    parsed_data = Column(JSONB, nullable=True)
    calculated_score = Column(Integer, nullable=True)
    has_hard_fail_flag = Column(Boolean, default=False)
    status = Column(String, nullable=False, default="NEW")
    is_manual_override = Column(Boolean, default=False)
    overridden_by_id = Column(UUID(as_uuid=True), nullable=True)
    overridden_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    job = relationship("Job", back_populates="applications")
    applicant = relationship("Applicant", back_populates="applications")
    answers = relationship("Answer", back_populates="application")

    __table_args__ = (
        Index('idx_app_job_id', 'job_id'),
        Index('idx_app_status', 'status'),
        Index('idx_app_applicant_id', 'applicant_id'),
        Index('idx_app_created_at', 'created_at'),
    )

class Answer(Base):
    __tablename__ = "answers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    job_question_id = Column(UUID(as_uuid=True), ForeignKey("job_questions.id"), nullable=False)
    applicant_answer = Column(String, nullable=False)
    is_passed = Column(Boolean, nullable=True)

    application = relationship("Application", back_populates="answers")

class StatusCount(Base):
    __tablename__ = "status_counts"
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), primary_key=True)
    status = Column(String, primary_key=True)
    count = Column(Integer, default=0, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    full_name = Column(String(100), nullable=True)

    sessions = relationship("Session", back_populates="user")

    __table_args__ = (
        Index('idx_users_email', 'email', unique=True),
    )

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_active_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="sessions")

