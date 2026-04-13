from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=1, max_length=120)
    role: Literal["student", "teacher"] = "student"
    group_id: int | None = None


class ProfilePayload(BaseModel):
    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    bio: str = Field(default="", max_length=300)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student_name: str
    role: Literal["student", "teacher"]
    user_id: int
    group_id: int | None = None
    group_name: str | None = None
    first_name: str = ""
    last_name: str = ""
    bio: str = ""


class SessionResponse(LoginResponse):
    pass


class ProfileResponse(BaseModel):
    user_id: int
    username: str
    role: Literal["student", "teacher"]
    first_name: str = ""
    last_name: str = ""
    bio: str = ""
    group_id: int | None = None
    group_name: str | None = None


class ProfileUpdateRequest(ProfilePayload):
    pass


class PasswordUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=120)
    new_password: str = Field(min_length=1, max_length=120)


class BasicSuccessResponse(BaseModel):
    success: bool = True
    message: str = "OK"


class GroupResponse(BaseModel):
    id: int
    name: str
    teacher: str
    student_count: int


class StudentSummary(BaseModel):
    id: int
    username: str
    first_name: str = ""
    last_name: str = ""


class SubjectResponse(BaseModel):
    id: int
    group_id: int
    name: str
    question_count: int = 0


class QuestionResponse(BaseModel):
    id: int
    group_id: int
    subject_id: int
    title: str
    text: str


class RandomQuestionResponse(QuestionResponse):
    pool_size: int
    subject_name: str


class AnswerSubmission(BaseModel):
    question_id: int
    answer: str = Field(min_length=2, max_length=5000)


class EvaluationResponse(BaseModel):
    question_id: int
    score: float
    feedback: str
    breakdown: dict[str, float]
    ai_copy_risk: float
    ai_copy_flag: bool


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class SubjectCreateRequest(BaseModel):
    group_id: int
    name: str = Field(min_length=2, max_length=120)


class QuestionCreateRequest(BaseModel):
    subject_id: int
    title: str = Field(min_length=2, max_length=160)
    text: str = Field(min_length=5, max_length=1000)
    minimum_words: int = Field(default=25, ge=5, le=500)


class TeacherQuestionResponse(QuestionResponse):
    subject_name: str
    submission_count: int = 0
    average_score: float = 0


class TeacherGroupDashboard(BaseModel):
    group: GroupResponse
    subjects: list[SubjectResponse]
    questions: list[TeacherQuestionResponse]


class TeacherStudentResult(BaseModel):
    result_id: int
    student_name: str
    group_name: str
    subject_name: str
    question_title: str
    score: float
    ai_copy_risk: float
    ai_copy_flag: bool
    created_at: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class TeacherDashboardResponse(BaseModel):
    teacher_name: str
    groups: list[TeacherGroupDashboard]
    totals: dict[str, Any]
    results: list[TeacherStudentResult]
    available_subjects: list[SubjectResponse]
    pagination: PaginationMeta
    results_pagination: PaginationMeta


class LogoutResponse(BaseModel):
    success: bool = True


class StudentSubjectsResponse(BaseModel):
    group_id: int
    group_name: str
    subjects: list[SubjectResponse]


class ResetStatisticsResponse(BaseModel):
    success: bool = True
