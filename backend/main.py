from __future__ import annotations

import math
import random
import sqlite3
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .data import APP_NAME
from .db import clear_statistics, create_token, get_connection, hash_password, init_db, json_dumps, json_loads
from .integration_api import evaluate_with_ai
from .schemas import (
    AnswerSubmission,
    BasicSuccessResponse,
    EvaluationResponse,
    GroupCreateRequest,
    GroupResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PaginationMeta,
    PasswordUpdateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    QuestionCreateRequest,
    RandomQuestionResponse,
    ResetStatisticsResponse,
    SessionResponse,
    StudentSubjectsResponse,
    SubjectCreateRequest,
    SubjectResponse,
    TeacherDashboardResponse,
    TeacherGroupDashboard,
    TeacherQuestionResponse,
    TeacherStudentResult,
    StudentSummary,
)

app = FastAPI(title=APP_NAME, version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    # During local development allow any origin (dev convenience). In production narrow this down.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


def _extract_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Avtorizatsiya talab qilinadi")
    return authorization.split(" ", 1)[1].strip()


def _display_name(row: sqlite3.Row) -> str:
    full_name = f"{row['first_name']} {row['last_name']}".strip()
    return full_name or row["username"]


def _build_session_response(row: sqlite3.Row, token: str) -> SessionResponse:
    return SessionResponse(
        access_token=token,
        student_name=_display_name(row),
        role=row["role"],
        user_id=row["id"],
        group_id=row["group_id"],
        group_name=row["group_name"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        bio=row["bio"],
    )


def _build_profile_response(row: sqlite3.Row) -> ProfileResponse:
    return ProfileResponse(
        user_id=row["id"],
        username=row["username"],
        role=row["role"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        bio=row["bio"],
        group_id=row["group_id"],
        group_name=row["group_name"],
    )


def get_current_user(token: str = Depends(_extract_token)) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.username, users.role, users.group_id, users.first_name, users.last_name,
                   users.bio, groups.name AS group_name, sessions.token
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            LEFT JOIN groups ON groups.id = users.group_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Sessiya topilmadi yoki tugagan")

    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "group_id": row["group_id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "bio": row["bio"],
        "group_name": row["group_name"],
        "token": row["token"],
    }


def require_teacher(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Faqat o'qituvchi uchun")
    return user


def require_student(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Faqat o'quvchi uchun")
    return user


def _group_row_to_response(row: sqlite3.Row) -> GroupResponse:
    return GroupResponse(
        id=row["id"],
        name=row["name"],
        teacher=row["teacher"],
        student_count=row["student_count"],
    )


def _list_groups(teacher_id: int | None = None, page: int | None = None, page_size: int | None = None) -> tuple[list[GroupResponse], int]:
    base_query = """
        FROM groups
        JOIN users AS teachers ON teachers.id = groups.teacher_id
        LEFT JOIN users AS students ON students.group_id = groups.id AND students.role = 'student'
    """
    where_clause = ""
    params: list[Any] = []
    if teacher_id is not None:
        where_clause = " WHERE groups.teacher_id = ?"
        params.append(teacher_id)

    with get_connection() as connection:
        total = connection.execute(f"SELECT COUNT(*) AS count FROM groups{where_clause}", tuple(params)).fetchone()["count"]
        query = f"""
            SELECT groups.id, groups.name, teachers.username AS teacher,
                   COUNT(DISTINCT students.id) AS student_count
            {base_query}
            {where_clause}
            GROUP BY groups.id, groups.name, teachers.username
            ORDER BY groups.name
        """
        if page is not None and page_size is not None:
            offset = max(page - 1, 0) * page_size
            query += " LIMIT ? OFFSET ?"
            rows = connection.execute(query, tuple([*params, page_size, offset])).fetchall()
        else:
            rows = connection.execute(query, tuple(params)).fetchall()

    return ([_group_row_to_response(row) for row in rows], total)


def _list_subjects(group_id: int | None = None, teacher_id: int | None = None) -> list[SubjectResponse]:
    query = """
        SELECT subjects.id, subjects.group_id, subjects.name, COUNT(questions.id) AS question_count
        FROM subjects
        JOIN groups ON groups.id = subjects.group_id
        LEFT JOIN questions ON questions.subject_id = subjects.id
    """
    conditions = []
    params: list[Any] = []
    if group_id is not None:
        conditions.append("subjects.group_id = ?")
        params.append(group_id)
    if teacher_id is not None:
        conditions.append("groups.teacher_id = ?")
        params.append(teacher_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY subjects.id, subjects.group_id, subjects.name ORDER BY subjects.name"

    with get_connection() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return [
        SubjectResponse(
            id=row["id"],
            group_id=row["group_id"],
            name=row["name"],
            question_count=row["question_count"],
        )
        for row in rows
    ]


def _list_teacher_questions(teacher_id: int, group_id: int) -> list[TeacherQuestionResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT questions.id, subjects.group_id, questions.subject_id, questions.title, questions.text,
                   subjects.name AS subject_name,
                   COUNT(results.id) AS submission_count,
                   COALESCE(AVG(results.score), 0) AS average_score
            FROM questions
            JOIN subjects ON subjects.id = questions.subject_id
            JOIN groups ON groups.id = subjects.group_id
            LEFT JOIN results ON results.question_id = questions.id
            WHERE groups.teacher_id = ? AND groups.id = ?
            GROUP BY questions.id, subjects.group_id, questions.subject_id, questions.title, questions.text, subjects.name
            ORDER BY subjects.name, questions.id DESC
            """,
            (teacher_id, group_id),
        ).fetchall()

    return [
        TeacherQuestionResponse(
            id=row["id"],
            group_id=row["group_id"],
            subject_id=row["subject_id"],
            title=row["title"],
            text=row["text"],
            subject_name=row["subject_name"],
            submission_count=row["submission_count"],
            average_score=round(float(row["average_score"] or 0), 2),
        )
        for row in rows
    ]


def _list_teacher_results(
    teacher_id: int,
    group_id: int | None = None,
    subject_id: int | None = None,
    student_query: str | None = None,
    score_range: str | None = None,
    ai_flag: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> tuple[list[TeacherStudentResult], int]:
    query = """
        SELECT results.id AS result_id, students.username AS username, students.first_name, students.last_name,
               groups.name AS group_name, subjects.name AS subject_name, questions.title AS question_title,
               results.score, results.ai_copy_risk, results.ai_copy_flag, results.created_at
        FROM results
        JOIN users AS students ON students.id = results.student_id
        JOIN groups ON groups.id = results.group_id
        JOIN subjects ON subjects.id = results.subject_id
        JOIN questions ON questions.id = results.question_id
        WHERE groups.teacher_id = ?
    """
    params: list[Any] = [teacher_id]
    if group_id is not None:
        query += " AND results.group_id = ?"
        params.append(group_id)
    if subject_id is not None:
        query += " AND results.subject_id = ?"
        params.append(subject_id)
    if student_query:
        query += " AND (students.username LIKE ? OR students.first_name LIKE ? OR students.last_name LIKE ?)"
        like_value = f"%{student_query.strip()}%"
        params.extend([like_value, like_value, like_value])
    if score_range:
        if score_range == "0-49":
            query += " AND results.score < 50"
        elif score_range == "50-69":
            query += " AND results.score >= 50 AND results.score < 70"
        elif score_range == "70-89":
            query += " AND results.score >= 70 AND results.score < 90"
        elif score_range == "90-100":
            query += " AND results.score >= 90"
    if ai_flag == "flagged":
        query += " AND results.ai_copy_flag = 1"
    elif ai_flag == "clean":
        query += " AND results.ai_copy_flag = 0"
    count_query = f"SELECT COUNT(*) AS count FROM ({query}) AS filtered_results"
    query += " ORDER BY results.created_at DESC, students.username"

    with get_connection() as connection:
        total = connection.execute(count_query, tuple(params)).fetchone()["count"]
        if page is not None and page_size is not None:
            offset = max(page - 1, 0) * page_size
            query += " LIMIT ? OFFSET ?"
            rows = connection.execute(query, tuple([*params, page_size, offset])).fetchall()
        else:
            rows = connection.execute(query, tuple(params)).fetchall()

    return ([
        TeacherStudentResult(
            result_id=row["result_id"],
            student_name=(f"{row['first_name']} {row['last_name']}".strip() or row["username"]),
            group_name=row["group_name"],
            subject_name=row["subject_name"],
            question_title=row["question_title"],
            score=round(float(row["score"]), 2),
            ai_copy_risk=round(float(row["ai_copy_risk"]), 2),
            ai_copy_flag=bool(row["ai_copy_flag"]),
            created_at=row["created_at"],
        )
        for row in rows
    ], total)


def _user_row(user_id: int) -> sqlite3.Row:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.username, users.role, users.group_id, users.first_name, users.last_name,
                   users.bio, users.password_hash, groups.name AS group_name
            FROM users
            LEFT JOIN groups ON groups.id = users.group_id
            WHERE users.id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return row


def _list_students_in_group(group_id: int) -> list[StudentSummary]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, username, first_name, last_name
            FROM users
            WHERE group_id = ? AND role = 'student'
            ORDER BY last_name, first_name, username
            """,
            (group_id,),
        ).fetchall()

    return [StudentSummary(id=row["id"], username=row["username"], first_name=row["first_name"], last_name=row["last_name"]) for row in rows]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME}


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    if payload.role == "student" and payload.group_id is None:
        raise HTTPException(status_code=400, detail="O'quvchi uchun guruh tanlash majburiy")

    with get_connection() as connection:
        if payload.role == "student":
            group_row = connection.execute("SELECT id FROM groups WHERE id = ?", (payload.group_id,)).fetchone()
            if group_row is None:
                raise HTTPException(status_code=404, detail="Tanlangan guruh topilmadi")

        existing = connection.execute(
            "SELECT id, password_hash, group_id FROM users WHERE username = ? AND role = ?",
            (payload.username.strip(), payload.role),
        ).fetchone()

        password_hash = hash_password(payload.password)
        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO users(username, password_hash, role, group_id, first_name, last_name, bio)
                VALUES (?, ?, ?, ?, '', '', '')
                """,
                (payload.username.strip(), password_hash, payload.role, payload.group_id),
            )
            user_id = cursor.lastrowid
        else:
            if existing["password_hash"] != password_hash:
                raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
            if payload.role == "student" and existing["group_id"] != payload.group_id:
                raise HTTPException(status_code=400, detail="Bu foydalanuvchi boshqa guruhga biriktirilgan")
            user_id = existing["id"]

        token = create_token()
        connection.execute("INSERT INTO sessions(token, user_id) VALUES (?, ?)", (token, user_id))

    return _build_session_response(_user_row(user_id), token)


@app.post("/logout", response_model=LogoutResponse)
def logout(user: dict[str, Any] = Depends(get_current_user)) -> LogoutResponse:
    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (user["token"],))
    return LogoutResponse()


@app.get("/me", response_model=SessionResponse)
def me(user: dict[str, Any] = Depends(get_current_user)) -> SessionResponse:
    return _build_session_response(_user_row(user["id"]), user["token"])


@app.get("/profile", response_model=ProfileResponse)
def get_profile(user: dict[str, Any] = Depends(get_current_user)) -> ProfileResponse:
    return _build_profile_response(_user_row(user["id"]))


@app.put("/profile", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdateRequest, user: dict[str, Any] = Depends(get_current_user)) -> ProfileResponse:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET first_name = ?, last_name = ?, bio = ?
            WHERE id = ?
            """,
            (payload.first_name.strip(), payload.last_name.strip(), payload.bio.strip(), user["id"]),
        )
    return _build_profile_response(_user_row(user["id"]))


@app.post("/profile/password", response_model=BasicSuccessResponse)
def change_password(payload: PasswordUpdateRequest, user: dict[str, Any] = Depends(get_current_user)) -> BasicSuccessResponse:
    row = _user_row(user["id"])
    if row["password_hash"] != hash_password(payload.current_password):
        raise HTTPException(status_code=400, detail="Joriy parol noto'g'ri")

    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(payload.new_password), user["id"]),
        )
    return BasicSuccessResponse(message="Parol yangilandi")


@app.get("/groups", response_model=list[GroupResponse])
def list_groups() -> list[GroupResponse]:
    groups, _ = _list_groups()
    return groups


@app.get("/student/subjects", response_model=StudentSubjectsResponse)
def student_subjects(user: dict[str, Any] = Depends(require_student)) -> StudentSubjectsResponse:
    if user["group_id"] is None:
        raise HTTPException(status_code=400, detail="O'quvchi guruhga biriktirilmagan")
    return StudentSubjectsResponse(
        group_id=user["group_id"],
        group_name=user["group_name"] or "",
        subjects=_list_subjects(group_id=user["group_id"]),
    )


@app.get("/questions/random", response_model=RandomQuestionResponse)
def get_random_question(subject_id: int, user: dict[str, Any] = Depends(require_student)) -> RandomQuestionResponse:
    with get_connection() as connection:
        subject = connection.execute(
            "SELECT id, name, group_id FROM subjects WHERE id = ?",
            (subject_id,),
        ).fetchone()
        if subject is None or subject["group_id"] != user["group_id"]:
            raise HTTPException(status_code=404, detail="Fan topilmadi yoki sizga tegishli emas")

        questions = connection.execute(
            """
            SELECT questions.id, questions.subject_id, questions.title, questions.text,
                   subjects.group_id, subjects.name AS subject_name
            FROM questions
            JOIN subjects ON subjects.id = questions.subject_id
            WHERE questions.subject_id = ?
            """,
            (subject_id,),
        ).fetchall()

    if not questions:
        raise HTTPException(status_code=404, detail="Bu fan uchun savollar topilmadi")

    question = random.choice(questions)
    return RandomQuestionResponse(
        id=question["id"],
        group_id=question["group_id"],
        subject_id=question["subject_id"],
        title=question["title"],
        text=question["text"],
        pool_size=len(questions),
        subject_name=question["subject_name"],
    )


@app.post("/submit-answer", response_model=EvaluationResponse)
def submit_answer(payload: AnswerSubmission, user: dict[str, Any] = Depends(require_student)) -> EvaluationResponse:
    with get_connection() as connection:
        question = connection.execute(
            """
            SELECT questions.id, questions.text, questions.reference_answer, questions.keywords_json, questions.minimum_words,
                   subjects.id AS subject_id, subjects.group_id
            FROM questions
            JOIN subjects ON subjects.id = questions.subject_id
            WHERE questions.id = ?
            """,
            (payload.question_id,),
        ).fetchone()

        if question is None:
            raise HTTPException(status_code=404, detail="Savol topilmadi")
        if question["group_id"] != user["group_id"]:
            raise HTTPException(status_code=403, detail="Bu savol sizning guruhingizga tegishli emas")

        result = evaluate_with_ai(
            answer=payload.answer,
            question_text=question["text"],
            reference_answer=question["reference_answer"],
            rubric={
                "minimum_words": question["minimum_words"],
                "keywords": json_loads(question["keywords_json"]),
                "weights": {"semantic": 0.7, "coverage": 0.2, "completeness": 0.1},
            },
        )

        connection.execute(
            """
            INSERT INTO results(student_id, group_id, subject_id, question_id, answer, score, feedback, breakdown_json, ai_copy_risk, ai_copy_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                question["group_id"],
                question["subject_id"],
                question["id"],
                payload.answer,
                result["score"],
                result["feedback"],
                json_dumps(result["breakdown"]),
                result["ai_copy_risk"],
                1 if result["ai_copy_flag"] else 0,
            ),
        )

    return EvaluationResponse(
        question_id=payload.question_id,
        score=result["score"],
        feedback=result["feedback"],
        breakdown=result["breakdown"],
        ai_copy_risk=result["ai_copy_risk"],
        ai_copy_flag=result["ai_copy_flag"],
    )


@app.post("/teacher/groups", response_model=GroupResponse)
def create_group(payload: GroupCreateRequest, teacher: dict[str, Any] = Depends(require_teacher)) -> GroupResponse:
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO groups(name, teacher_id) VALUES (?, ?)",
                (payload.name.strip(), teacher["id"]),
            )
            row = connection.execute(
                """
                SELECT groups.id, groups.name, users.username AS teacher, 0 AS student_count
                FROM groups JOIN users ON users.id = groups.teacher_id
                WHERE groups.id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Bu nomdagi guruh allaqachon mavjud")
    return _group_row_to_response(row)


@app.post("/teacher/subjects", response_model=SubjectResponse)
def create_subject(payload: SubjectCreateRequest, teacher: dict[str, Any] = Depends(require_teacher)) -> SubjectResponse:
    with get_connection() as connection:
        group = connection.execute(
            "SELECT id FROM groups WHERE id = ? AND teacher_id = ?",
            (payload.group_id, teacher["id"]),
        ).fetchone()
        if group is None:
            raise HTTPException(status_code=404, detail="Guruh topilmadi")
        try:
            cursor = connection.execute(
                "INSERT INTO subjects(group_id, name) VALUES (?, ?)",
                (payload.group_id, payload.name.strip()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Bu fan ushbu guruhga allaqachon qo'shilgan")
    return SubjectResponse(id=cursor.lastrowid, group_id=payload.group_id, name=payload.name.strip(), question_count=0)


@app.post("/teacher/questions", response_model=TeacherQuestionResponse)
def create_question(payload: QuestionCreateRequest, teacher: dict[str, Any] = Depends(require_teacher)) -> TeacherQuestionResponse:
    with get_connection() as connection:
        subject = connection.execute(
            """
            SELECT subjects.id, subjects.group_id, subjects.name
            FROM subjects
            JOIN groups ON groups.id = subjects.group_id
            WHERE subjects.id = ? AND groups.teacher_id = ?
            """,
            (payload.subject_id, teacher["id"]),
        ).fetchone()
        if subject is None:
            raise HTTPException(status_code=404, detail="Fan topilmadi")

        cursor = connection.execute(
            """
            INSERT INTO questions(subject_id, title, text, reference_answer, keywords_json, minimum_words)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.subject_id,
                payload.title.strip(),
                payload.text.strip(),
                "",
                json_dumps([]),
                payload.minimum_words,
            ),
        )

    return TeacherQuestionResponse(
        id=cursor.lastrowid,
        group_id=subject["group_id"],
        subject_id=payload.subject_id,
        title=payload.title.strip(),
        text=payload.text.strip(),
        subject_name=subject["name"],
        submission_count=0,
        average_score=0,
    )


@app.post("/teacher/reset-statistics", response_model=ResetStatisticsResponse)
def reset_statistics(_: dict[str, Any] = Depends(require_teacher)) -> ResetStatisticsResponse:
    clear_statistics()
    return ResetStatisticsResponse()


@app.get("/teacher/dashboard", response_model=TeacherDashboardResponse)
def teacher_dashboard(
    group_id: int | None = None,
    subject_id: int | None = None,
    student_query: str | None = None,
    score_range: str | None = None,
    ai_flag: str | None = None,
    page: int = 1,
    page_size: int = 6,
    results_page: int = 1,
    results_page_size: int = 10,
    teacher: dict[str, Any] = Depends(require_teacher),
) -> TeacherDashboardResponse:
    page = max(page, 1)
    page_size = max(1, min(page_size, 20))
    results_page = max(results_page, 1)
    results_page_size = max(1, min(results_page_size, 30))

    groups, total_groups = _list_groups(teacher_id=teacher["id"], page=page, page_size=page_size)
    all_groups, _ = _list_groups(teacher_id=teacher["id"])

    dashboard_groups = []
    for group in groups:
        subjects = _list_subjects(group_id=group.id, teacher_id=teacher["id"])
        filtered_questions = _list_teacher_questions(teacher["id"], group.id)
        if subject_id is not None:
            subjects = [subject for subject in subjects if subject.id == subject_id]
            filtered_questions = [question for question in filtered_questions if question.subject_id == subject_id]
        dashboard_groups.append(TeacherGroupDashboard(group=group, subjects=subjects, questions=filtered_questions))

    results, total_results = _list_teacher_results(
        teacher["id"],
        group_id=group_id,
        subject_id=subject_id,
        student_query=student_query,
        score_range=score_range,
        ai_flag=ai_flag,
        page=results_page,
        page_size=results_page_size,
    )
    all_subjects = _list_subjects(teacher_id=teacher["id"])
    totals = {
        "groups": total_groups,
        "subjects": len(all_subjects),
        "questions": sum(len(group.questions) for group in dashboard_groups),
        "submissions": total_results,
    }
    total_pages = max(1, math.ceil(total_groups / page_size)) if total_groups else 1
    results_total_pages = max(1, math.ceil(total_results / results_page_size)) if total_results else 1

    return TeacherDashboardResponse(
        teacher_name=(f"{teacher['first_name']} {teacher['last_name']}".strip() or teacher["username"]),
        groups=dashboard_groups,
        totals=totals,
        results=results,
        available_subjects=all_subjects,
        pagination=PaginationMeta(page=page, page_size=page_size, total_items=total_groups, total_pages=total_pages),
        results_pagination=PaginationMeta(
            page=results_page,
            page_size=results_page_size,
            total_items=total_results,
            total_pages=results_total_pages,
        ),
    )


@app.get("/teacher/groups/{group_id}/students", response_model=list[StudentSummary])
def teacher_group_students(group_id: int, teacher: dict[str, Any] = Depends(require_teacher)) -> list[StudentSummary]:
    # Verify teacher actually owns the group
    with get_connection() as connection:
        row = connection.execute("SELECT teacher_id FROM groups WHERE id = ?", (group_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Guruh topilmadi")
        if row["teacher_id"] != teacher["id"]:
            raise HTTPException(status_code=403, detail="Siz bu guruh ustasi emassiz")

    return _list_students_in_group(group_id)


@app.get("/teacher/subjects/{subject_id}/questions", response_model=list[TeacherQuestionResponse])
def teacher_subject_questions(subject_id: int, teacher: dict[str, Any] = Depends(require_teacher)) -> list[TeacherQuestionResponse]:
    # Verify teacher owns the subject via its group
    with get_connection() as connection:
        row = connection.execute(
            "SELECT subjects.id FROM subjects JOIN groups ON groups.id = subjects.group_id WHERE subjects.id = ? AND groups.teacher_id = ?",
            (subject_id, teacher["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Fan topilmadi yoki sizga tegishli emas")

        rows = connection.execute(
            """
            SELECT questions.id, subjects.group_id, questions.subject_id, questions.title, questions.text,
                   subjects.name AS subject_name,
                   COUNT(results.id) AS submission_count,
                   COALESCE(AVG(results.score), 0) AS average_score
            FROM questions
            JOIN subjects ON subjects.id = questions.subject_id
            LEFT JOIN results ON results.question_id = questions.id
            WHERE questions.subject_id = ?
            GROUP BY questions.id, subjects.group_id, questions.subject_id, questions.title, questions.text, subjects.name
            ORDER BY questions.id DESC
            """,
            (subject_id,),
        ).fetchall()

    return [
        TeacherQuestionResponse(
            id=row["id"],
            group_id=row["group_id"],
            subject_id=row["subject_id"],
            title=row["title"],
            text=row["text"],
            subject_name=row["subject_name"],
            submission_count=row["submission_count"],
            average_score=round(float(row["average_score"] or 0), 2),
        )
        for row in rows
    ]


@app.get("/teacher/questions/{question_id}", response_model=TeacherQuestionResponse)
def teacher_get_question(question_id: int, teacher: dict[str, Any] = Depends(require_teacher)) -> TeacherQuestionResponse:
    # Verify teacher owns the subject via its group and return aggregated question info
    with get_connection() as connection:
        row = connection.execute(
            "SELECT questions.id FROM questions JOIN subjects ON subjects.id = questions.subject_id JOIN groups ON groups.id = subjects.group_id WHERE questions.id = ? AND groups.teacher_id = ?",
            (question_id, teacher["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Savol topilmadi yoki sizga tegishli emas")

        qrow = connection.execute(
            """
            SELECT questions.id, subjects.group_id, questions.subject_id, questions.title, questions.text,
                   subjects.name AS subject_name,
                   COUNT(results.id) AS submission_count,
                   COALESCE(AVG(results.score), 0) AS average_score
            FROM questions
            JOIN subjects ON subjects.id = questions.subject_id
            LEFT JOIN results ON results.question_id = questions.id
            WHERE questions.id = ?
            GROUP BY questions.id, subjects.group_id, questions.subject_id, questions.title, questions.text, subjects.name
            """,
            (question_id,),
        ).fetchone()

    if qrow is None:
        raise HTTPException(status_code=404, detail="Savol topilmadi")

    return TeacherQuestionResponse(
        id=qrow["id"],
        group_id=qrow["group_id"],
        subject_id=qrow["subject_id"],
        title=qrow["title"],
        text=qrow["text"],
        subject_name=qrow["subject_name"],
        submission_count=qrow["submission_count"],
        average_score=round(float(qrow["average_score"] or 0), 2),
    )


@app.get("/teacher/users/{user_id}", response_model=ProfileResponse)
def teacher_get_user_profile(user_id: int, teacher: dict[str, Any] = Depends(require_teacher)) -> ProfileResponse:
    # Allow teacher to fetch profile of a student in their groups
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, username, role, first_name, last_name, bio, group_id, (SELECT name FROM groups WHERE id = users.group_id) AS group_name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

        # If the target user is a student, ensure they belong to one of the teacher's groups
        if row["role"] == "student":
            # check that teacher owns the group
            g = connection.execute("SELECT id FROM groups WHERE id = ? AND teacher_id = ?", (row["group_id"], teacher["id"])).fetchone()
            if g is None:
                raise HTTPException(status_code=403, detail="Siz bu foydalanuvchi profilini ko'ra olmaysiz")

    return ProfileResponse(
        user_id=row["id"],
        username=row["username"],
        role=row["role"],
        first_name=row["first_name"] or "",
        last_name=row["last_name"] or "",
        bio=row["bio"] or "",
        group_id=row["group_id"],
        group_name=row["group_name"],
    )
