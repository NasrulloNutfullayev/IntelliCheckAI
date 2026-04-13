SELECT id, username, role, first_name, last_name, bio FROM users;
SELECT id, name, teacher_id FROM groups;
SELECT id, group_id, name FROM subjects;
SELECT id, subject_id, title, minimum_words FROM questions;
SELECT question_id, COUNT(*) AS result_count FROM results GROUP BY question_id ORDER BY question_id;
SELECT id, student_id, question_id, score, ai_copy_risk, created_at FROM results ORDER BY id DESC;

-- Demo login:
-- teacher: username=teacher_demo password=teacher123
-- student: username=ali01 password=student123
