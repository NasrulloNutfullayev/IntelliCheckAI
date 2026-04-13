from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "intellicheck.db"


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def now_expression() -> str:
    return "datetime('now')"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token() -> str:
    return secrets.token_urlsafe(32)


def json_dumps(payload) -> str:
    return json.dumps(payload, ensure_ascii=False)


def json_loads(payload: str | None):
    if not payload:
        return {}
    return json.loads(payload)


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'teacher')),
                group_id INTEGER,
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(username, role)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                teacher_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(teacher_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
                UNIQUE(group_id, name)
            );

            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                reference_answer TEXT NOT NULL,
                keywords_json TEXT NOT NULL DEFAULT '[]',
                minimum_words INTEGER NOT NULL DEFAULT 25,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer TEXT NOT NULL,
                score REAL NOT NULL,
                feedback TEXT NOT NULL,
                breakdown_json TEXT NOT NULL DEFAULT '{}',
                ai_copy_risk REAL NOT NULL DEFAULT 0,
                ai_copy_flag INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(student_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_column(connection, "users", "first_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "users", "last_name", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "users", "bio", "TEXT NOT NULL DEFAULT ''")
        _seed_demo_data(connection)


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_definition: str) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def clear_statistics() -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM results")


def _seed_demo_data(connection: sqlite3.Connection) -> None:
    has_groups = connection.execute("SELECT COUNT(*) AS count FROM groups").fetchone()["count"]
    has_questions = connection.execute("SELECT COUNT(*) AS count FROM questions").fetchone()["count"]
    existing_result_count = connection.execute("SELECT COUNT(*) AS count FROM results").fetchone()["count"] if has_groups and has_questions else 0
    if has_groups and has_questions and existing_result_count and _all_questions_have_minimum_results(connection, minimum=5):
        return

    teacher_password = hash_password("teacher123")
    student_password = hash_password("student123")

    teacher = connection.execute(
        """
        INSERT OR IGNORE INTO users(username, password_hash, role, group_id, first_name, last_name, bio)
        VALUES ('teacher_demo', ?, 'teacher', NULL, 'Demo', 'Teacher', 'Yozma nazorat uchun demo o''qituvchi')
        """,
        (teacher_password,),
    )
    teacher_row = connection.execute("SELECT id FROM users WHERE username = 'teacher_demo' AND role = 'teacher'").fetchone()
    teacher_id = teacher_row["id"]

    groups = [
        ("AI-101", teacher_id),
        ("Python-202", teacher_id),
    ]
    for name, tid in groups:
        connection.execute("INSERT OR IGNORE INTO groups(name, teacher_id) VALUES (?, ?)", (name, tid))

    group_map = {
        row["name"]: row["id"]
        for row in connection.execute("SELECT id, name FROM groups").fetchall()
    }

    subjects = [
        (group_map["AI-101"], "Sun'iy intellekt"),
        (group_map["AI-101"], "Machine Learning"),
        (group_map["Python-202"], "Python asoslari"),
        (group_map["Python-202"], "Algoritmlar"),
    ]
    for gid, name in subjects:
        connection.execute("INSERT OR IGNORE INTO subjects(group_id, name) VALUES (?, ?)", (gid, name))

    subject_map = {
        (row["group_id"], row["name"]): row["id"]
        for row in connection.execute("SELECT id, group_id, name FROM subjects").fetchall()
    }

    questions = [
        (subject_map[(group_map["AI-101"], "Sun'iy intellekt")], "AI tushunchasi", "Sun'iy intellekt nima va qayerlarda ishlatiladi?", 30),
        (subject_map[(group_map["AI-101"], "Sun'iy intellekt")], "Expert system", "Expert system qanday ishlaydi?", 25),
        (subject_map[(group_map["AI-101"], "Machine Learning")], "Supervised learning", "Supervised learning mohiyatini tushuntiring.", 30),
        (subject_map[(group_map["AI-101"], "Machine Learning")], "Overfitting", "Overfitting nima va uni kamaytirish yo'llari?", 35),
        (subject_map[(group_map["Python-202"], "Python asoslari")], "Python tipi", "Python da list va tuple farqi nima?", 20),
        (subject_map[(group_map["Python-202"], "Python asoslari")], "Funksiya", "Python funksiyasi nima uchun kerak?", 20),
        (subject_map[(group_map["Python-202"], "Algoritmlar")], "Algoritm", "Algoritm nima va nima uchun muhim?", 25),
        (subject_map[(group_map["Python-202"], "Algoritmlar")], "Murakkablik", "Vaqt murakkabligi nimani bildiradi?", 25),
    ]
    for sid, title, text, min_words in questions:
        connection.execute(
            """
            INSERT OR IGNORE INTO questions(subject_id, title, text, reference_answer, keywords_json, minimum_words)
            VALUES (?, ?, ?, '', '[]', ?)
            """,
            (sid, title, text, min_words),
        )

    students = [
        ("ali01", group_map["AI-101"], "Ali", "Karimov"),
        ("dilnoza02", group_map["AI-101"], "Dilnoza", "Tursunova"),
        ("behruz03", group_map["AI-101"], "Behruz", "Saidov"),
        ("malika04", group_map["Python-202"], "Malika", "Ergasheva"),
        ("javohir05", group_map["Python-202"], "Javohir", "Yuldashev"),
        ("nilufar06", group_map["Python-202"], "Nilufar", "Rasulova"),
    ]
    for username, gid, first_name, last_name in students:
        connection.execute(
            """
            INSERT OR IGNORE INTO users(username, password_hash, role, group_id, first_name, last_name, bio)
            VALUES (?, ?, 'student', ?, ?, ?, 'Demo student')
            """,
            (username, student_password, gid, first_name, last_name),
        )

    student_rows = connection.execute(
        "SELECT id, group_id FROM users WHERE role = 'student' ORDER BY id"
    ).fetchall()
    student_by_group: dict[int, list[int]] = {}
    for row in student_rows:
        student_by_group.setdefault(row["group_id"], []).append(row["id"])

    question_rows = connection.execute(
        """
        SELECT questions.id, questions.title, questions.text, questions.minimum_words, subjects.id AS subject_id, subjects.group_id
        FROM questions JOIN subjects ON subjects.id = questions.subject_id
        ORDER BY questions.id
        """
    ).fetchall()

    feedbacks = [
        "Javob yetarli darajada mazmunli.",
        "Javob yaxshi, lekin ayrim tushunchalar qisqa yoritilgan.",
        "Javob o'rtacha baholandi.",
        "Javob mazmunan to'g'ri va aniq.",
        "Javobda asosiy fikrlar bor.",
    ]

    for index, question in enumerate(question_rows):
        students_for_group = student_by_group.get(question["group_id"], [])
        existing_for_question = connection.execute(
            "SELECT COUNT(*) AS count FROM results WHERE question_id = ?",
            (question["id"],),
        ).fetchone()["count"]
        needed = max(0, 5 - existing_for_question)
        for offset in range(needed):
            if not students_for_group:
                continue
            student_id = students_for_group[offset % len(students_for_group)]
            score = round(62 + ((index * 7 + offset * 5) % 31), 2)
            ai_risk = round(18 + ((index * 9 + offset * 6) % 37), 2)
            breakdown = {
                "mazmun_mosligi": round(min(score + 6, 98), 2),
                "tushuncha_qamrovi": round(min(score - 4, 95), 2),
                "toliqlik": round(min(score + 2, 97), 2),
                "ai_copy_risk": ai_risk,
            }
            answer = (
                f"{question['title']} bo'yicha demo javob {offset + 1}. "
                f"{question['text']} savoliga qisqa va tekshirilgan namunaviy fikr kiritildi."
            )
            connection.execute(
                """
                INSERT INTO results(student_id, group_id, subject_id, question_id, answer, score, feedback, breakdown_json, ai_copy_risk, ai_copy_flag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    student_id,
                    question["group_id"],
                    question["subject_id"],
                    question["id"],
                    answer,
                    score,
                    feedbacks[offset % len(feedbacks)],
                    json_dumps(breakdown),
                    ai_risk,
                ),
            )


def _all_questions_have_minimum_results(connection: sqlite3.Connection, minimum: int) -> bool:
    rows = connection.execute(
        """
        SELECT questions.id, COUNT(results.id) AS result_count
        FROM questions
        LEFT JOIN results ON results.question_id = questions.id
        GROUP BY questions.id
        """
    ).fetchall()
    return all(row["result_count"] >= minimum for row in rows)
