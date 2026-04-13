import React, { useEffect, useMemo, useState } from "react";
import {
  clearToken, createGroup, createQuestion, createSubject, fetchGroups, fetchProfile,
  fetchRandomQuestion, fetchSession, fetchStudentSubjects, fetchTeacherDashboard,
  loginStudent, logout, resetStatistics, submitAnswer, updatePassword, updateProfile,
  fetchGroupStudents, fetchUserProfile, fetchSubjectQuestions,
  fetchQuestion,
} from "./api";

const APP_NAME = import.meta.env.VITE_APP_NAME || "IntelliCheck AI";
const EXAM_SECONDS = 600;
const PAGE_SIZE = 6;

const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

function Toasts({ items, onClose }) {
  return <div className="toast-stack">{items.map((t) => <div key={t.id} className={`toast-item toast-${t.type}`}><div><strong>{t.title}</strong><p>{t.message}</p></div><button className="toast-close" onClick={() => onClose(t.id)}>Yopish</button></div>)}</div>;
}

function Landing({ onEnter }) {
  return <main className="landing-layout neon-grid"><section className="hero-panel"><p className="eyebrow">Yozma imtihon platformasi</p><h1>{APP_NAME}</h1><p className="feedback">Teacher va student oqimlari alohida sahifalarga bo'lingan, profil va AI risk ham bor.</p><div className="button-row"><button onClick={onEnter}>Kirish</button></div></section><section className="landing-grid"><article className="panel neon-panel"><p className="eyebrow">Teacher</p><h2>Alohida page lar</h2><p className="info-text">Dashboard, guruh, fan, savol va profil ajratilgan.</p></article><article className="panel neon-panel"><p className="eyebrow">Student</p><h2>Tez topshirish</h2><p className="info-text">Fan tanlanadi, savol random tushadi.</p></article><article className="panel neon-panel"><p className="eyebrow">Toasts</p><h2>Yengil feedback</h2><p className="info-text">Saqlash va xatoliklar toaster bilan chiqadi.</p></article></section></main>;
}

function Login({ onLogin, onBack }) {
  const [username, setUsername] = useState(""); const [password, setPassword] = useState("");
  const [role, setRole] = useState("student"); const [groupId, setGroupId] = useState("");
  const [groups, setGroups] = useState([]); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { fetchGroups().then(setGroups).catch((e) => setError(e.message)); }, []);
  useEffect(() => { if (!groupId && groups.length) setGroupId(String(groups[0].id)); }, [groups, groupId]);
  async function submit(e) {
    e.preventDefault(); setLoading(true); setError("");
    try { onLogin(await loginStudent({ username, password, role, group_id: role === "student" ? Number(groupId) : null })); }
    catch (err) { setError(err.message); } finally { setLoading(false); }
  }
  return <main className="auth-layout neon-grid"><section className="auth-copy"><p className="eyebrow">Kirish</p><h1>{APP_NAME}</h1><p>Sessiya saqlanadi va logout bilan yopiladi.</p><button className="ghost-button" onClick={onBack}>Bosh sahifa</button></section><section className="panel neon-panel"><h2>Kirish</h2><form onSubmit={submit}><div className="role-switch"><button type="button" className={role === "student" ? "active" : ""} onClick={() => setRole("student")}>O'quvchi</button><button type="button" className={role === "teacher" ? "active" : ""} onClick={() => setRole("teacher")}>O'qituvchi</button></div><label>Login<input value={username} onChange={(e) => setUsername(e.target.value)} required /></label><label>Parol<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>{role === "student" && <label>Guruh<select value={groupId} onChange={(e) => setGroupId(e.target.value)}>{groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></label>}{error && <p className="error">{error}</p>}<button disabled={loading}>{loading ? "Kirilmoqda..." : "Kirish"}</button></form></section></main>;
}

function Profile({ session, onBack, setSession, notify }) {
  const [form, setForm] = useState({ first_name: "", last_name: "", bio: "" });
  const [pass, setPass] = useState({ current_password: "", new_password: "" }); const [error, setError] = useState("");
  useEffect(() => { fetchProfile().then((p) => setForm({ first_name: p.first_name || "", last_name: p.last_name || "", bio: p.bio || "" })).catch((e) => setError(e.message)); }, []);
  async function saveProfile(e) {
    e.preventDefault(); setError("");
    try {
      const p = await updateProfile(form);
      setSession((s) => ({ ...s, student_name: `${p.first_name} ${p.last_name}`.trim() || s.student_name, first_name: p.first_name, last_name: p.last_name, bio: p.bio }));
      notify("success", "Profil saqlandi", "Profil ma'lumotlari yangilandi.");
    } catch (err) { setError(err.message); notify("error", "Profil saqlanmadi", err.message); }
  }
  async function savePass(e) {
    e.preventDefault(); setError("");
    try { const r = await updatePassword(pass); setPass({ current_password: "", new_password: "" }); notify("success", "Parol yangilandi", r.message); }
    catch (err) { setError(err.message); notify("error", "Parol yangilanmadi", err.message); }
  }
  return <main className="dashboard-content profile-page"><header className="topbar"><div><p className="eyebrow">Profil</p><h1>{session.student_name}</h1></div><button className="ghost-button" onClick={onBack}>Ortga</button></header><section className="profile-grid"><section className="panel neon-panel"><form onSubmit={saveProfile}><div className="two-column"><label>Ism<input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></label><label>Familiya<input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></label></div><label>Bio<textarea className="compact-textarea" value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} /></label><button>Profilni saqlash</button></form></section><section className="panel neon-panel"><h2>Parol</h2><form onSubmit={savePass}><label>Joriy parol<input type="password" value={pass.current_password} onChange={(e) => setPass({ ...pass, current_password: e.target.value })} required /></label><label>Yangi parol<input type="password" value={pass.new_password} onChange={(e) => setPass({ ...pass, new_password: e.target.value })} required /></label><button>Parolni yangilash</button></form>{error && <p className="error">{error}</p>}</section></section></main>;
}

function StudentHome({ session, onStart, onProfile, onLogout }) {
  const [subjects, setSubjects] = useState([]); const [subjectId, setSubjectId] = useState(""); const [error, setError] = useState("");
  useEffect(() => { fetchStudentSubjects().then((d) => { setSubjects(d.subjects); if (d.subjects.length) setSubjectId(String(d.subjects[0].id)); }).catch((e) => setError(e.message)); }, []);
  return <main className="result-layout neon-grid"><section className="result-summary"><p className="eyebrow">Xush kelibsiz</p><h1>{session.student_name}</h1><p className="feedback">{session.group_name} guruhi uchun fan tanlang.</p><div className="button-row"><button onClick={() => onStart(subjectId)} disabled={!subjectId}>Imtihonni boshlash</button><button className="ghost-button" onClick={onProfile}>Profil</button><button className="ghost-button" onClick={onLogout}>Chiqish</button></div></section><section className="panel neon-panel"><h2>Fan tanlash</h2><label>Fan<select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>{subjects.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.question_count} savol)</option>)}</select></label>{error && <p className="error">{error}</p>}</section></main>;
}

function Exam({ session, subjectId, onDone, onBack }) {
  const [question, setQuestion] = useState(null); const [answer, setAnswer] = useState(""); const [timeLeft, setTimeLeft] = useState(EXAM_SECONDS); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  useEffect(() => { fetchRandomQuestion(subjectId).then(setQuestion).catch((e) => setError(e.message)); }, [subjectId]);
  useEffect(() => { if (timeLeft <= 0) return undefined; const t = window.setInterval(() => setTimeLeft((v) => v - 1), 1000); return () => window.clearInterval(t); }, [timeLeft]);
  async function submit(e) { e.preventDefault(); if (!question) return; setLoading(true); setError(""); try { onDone({ ...(await submitAnswer({ question_id: question.id, answer })), question }); } catch (err) { setError(err.message); } finally { setLoading(false); } }
  return <main className="exam-layout neon-grid"><header className="topbar"><div><p className="eyebrow">{session.group_name}</p><h1>Imtihon</h1></div><div className="button-row"><div className="timer">{fmt(timeLeft)}</div><button className="ghost-button" onClick={onBack}>Ortga</button></div></header><section className="exam-grid"><article className="question-area neon-panel"><p className="eyebrow">{question?.subject_name || "Fan"}</p><h2>{question?.title || "Savol yuklanmoqda..."}</h2><p>{question?.text || "Savol topilmadi."}</p>{question && <p className="info-text">Random havza: {question.pool_size} ta savol</p>}</article><form className="answer-area neon-panel" onSubmit={submit}><label>Javob<textarea value={answer} onChange={(e) => setAnswer(e.target.value)} required /></label><div className="form-footer"><span>{answer.trim().split(/\s+/).filter(Boolean).length} ta so'z</span><button disabled={!question || loading || timeLeft <= 0}>{loading ? "Tekshirilmoqda..." : "Yuborish"}</button></div>{error && <p className="error">{error}</p>}</form></section></main>;
}

function Result({ result, onRestart, onProfile, onLogout }) {
  const items = useMemo(() => [["Mazmun mosligi", result.breakdown?.mazmun_mosligi || 0], ["Tushuncha qamrovi", result.breakdown?.tushuncha_qamrovi || 0], ["To'liqlik", result.breakdown?.toliqlik || 0], ["AI copy risk", result.ai_copy_risk || 0]], [result]);
  return <main className="result-layout neon-grid"><section className="result-summary"><p className="eyebrow">Natija</p><h1>{result.ai_copy_flag ? "Tekshiruv to'xtatildi" : "Baholash natijasi"}</h1><div className="score">{result.ai_copy_flag ? "0" : result.score}</div><p className="feedback">{result.feedback}</p><div className="button-row"><button onClick={onRestart}>Yangi fan tanlash</button><button className="ghost-button" onClick={onProfile}>Profil</button><button className="ghost-button" onClick={onLogout}>Chiqish</button></div></section><section className="panel neon-panel"><h2>Tafsilot</h2>{items.map(([l, v]) => <div key={l} className="breakdown-row"><span>{l}</span><strong>{v}%</strong></div>)}</section></main>;
}

function TeacherNav({ active, onNav, onLogout }) {
  const items = [["dashboard", "Dashboard"], ["groups", "Guruhlar"], ["subjects", "Fanlar"], ["questions", "Savollar"], ["profile", "Profil"]];
  return <aside className="panel neon-panel teacher-nav"><h2>Bo'limlar</h2><div className="nav-list">{items.map(([id, label]) => <button key={id} className={active === id ? "selector-card selected" : "selector-card"} onClick={() => onNav(id)}><strong>{label}</strong></button>)}</div><button className="ghost-button" onClick={onLogout}>Chiqish</button></aside>;
}

function TeacherDashboard({ session, notify }) {
  const [data, setData] = useState(null); const [groupId, setGroupId] = useState(""); const [subjectId, setSubjectId] = useState(""); const [studentQuery, setStudentQuery] = useState(""); const [scoreRange, setScoreRange] = useState(""); const [aiFlag, setAiFlag] = useState(""); const [page, setPage] = useState(1); const [resultsPage, setResultsPage] = useState(1); const [error, setError] = useState("");
  async function load(next = {}) {
    const g = next.groupId ?? groupId; const s = next.subjectId ?? subjectId; const q = next.studentQuery ?? studentQuery; const sr = next.scoreRange ?? scoreRange; const af = next.aiFlag ?? aiFlag; const p = next.page ?? page; const rp = next.resultsPage ?? resultsPage;
    try { const res = await fetchTeacherDashboard({ groupId: g || "", subjectId: s || "", studentQuery: q || "", scoreRange: sr || "", aiFlag: af || "", page: p, pageSize: PAGE_SIZE, resultsPage: rp, resultsPageSize: 10 }); setData(res); setGroupId(g); setSubjectId(s); setStudentQuery(q); setScoreRange(sr); setAiFlag(af); setPage(p); setResultsPage(rp); }
    catch (err) { setError(err.message); }
  }
  useEffect(() => { load({ groupId: "", subjectId: "", page: 1 }); }, []);
  if (!data) return <main className="dashboard-content"><p className="eyebrow">Dashboard yuklanmoqda...</p></main>;
  const subjects = groupId ? data.available_subjects.filter((s) => String(s.group_id) === String(groupId)) : data.available_subjects;
  return <main className="dashboard-content"><header className="topbar"><div><p className="eyebrow">Dashboard</p><h1>{session.student_name}</h1></div><button className="ghost-button" onClick={async () => { try { await resetStatistics(); notify("success", "Reset bajarildi", "Statistika tozalandi."); await load({ page: 1, resultsPage: 1 }); } catch (e) { setError(e.message); notify("error", "Reset bajarilmadi", e.message); } }}>Statistikani reset qilish</button></header><section className="stats-grid"><div className="stat-card neon-panel"><span>Guruhlar</span><strong>{data.totals.groups}</strong></div><div className="stat-card neon-panel"><span>Fanlar</span><strong>{data.totals.subjects}</strong></div><div className="stat-card neon-panel"><span>Savollar</span><strong>{data.totals.questions}</strong></div><div className="stat-card neon-panel"><span>Natijalar</span><strong>{data.totals.submissions}</strong></div></section><section className="panel neon-panel"><h2>Filtrlar</h2><div className="filter-grid"><label>Guruh<select value={groupId} onChange={(e) => load({ groupId: e.target.value, subjectId: "", page: 1, resultsPage: 1 })}><option value="">Barchasi</option>{data.groups.map((g) => <option key={g.group.id} value={g.group.id}>{g.group.name}</option>)}</select></label><label>Fan<select value={subjectId} onChange={(e) => load({ subjectId: e.target.value, page: 1, resultsPage: 1 })}><option value="">Barchasi</option>{subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label>Student qidirish<input value={studentQuery} onChange={(e) => setStudentQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") load({ studentQuery: e.currentTarget.value, resultsPage: 1 }); }} placeholder="Ali, Dilnoza..." /></label><label>Ball oralig'i<select value={scoreRange} onChange={(e) => load({ scoreRange: e.target.value, resultsPage: 1 })}><option value="">Barchasi</option><option value="0-49">0-49</option><option value="50-69">50-69</option><option value="70-89">70-89</option><option value="90-100">90-100</option></select></label><label>AI flag<select value={aiFlag} onChange={(e) => load({ aiFlag: e.target.value, resultsPage: 1 })}><option value="">Barchasi</option><option value="flagged">Faqat AI flag borlar</option><option value="clean">Faqat toza javoblar</option></select></label><div className="filter-actions"><button onClick={() => load({ studentQuery, resultsPage: 1 })}>Qidirish</button><button className="ghost-button" onClick={() => load({ groupId: "", subjectId: "", studentQuery: "", scoreRange: "", aiFlag: "", page: 1, resultsPage: 1 })}>Tozalash</button></div></div></section><section className="panel neon-panel"><h2>Natijalar</h2><div className="results-table">{data.results.length ? data.results.map((r) => <div key={r.result_id} className="result-row"><div><strong>{r.student_name}</strong><p>{r.group_name} / {r.subject_name}</p><p>{r.question_title}</p></div><div className="result-metrics"><strong>{r.score}%</strong><span className={r.ai_copy_flag ? "error" : "info-text"}>AI risk: {r.ai_copy_risk}%</span></div></div>) : <p className="empty-text">Hali natijalar yo'q.</p>}</div><div className="pagination-row"><button className="ghost-button" disabled={data.results_pagination.page <= 1} onClick={() => load({ resultsPage: resultsPage - 1 })}>Oldingi</button><span>{data.results_pagination.page} / {data.results_pagination.total_pages}</span><button className="ghost-button" disabled={data.results_pagination.page >= data.results_pagination.total_pages} onClick={() => load({ resultsPage: resultsPage + 1 })}>Keyingi</button></div>{error && <p className="error">{error}</p>}</section></main>;
}

function TeacherGroups({ notify, onOpenGroup }) {
  const [name, setName] = useState("");
  const [groups, setGroups] = useState([]);
  const [error, setError] = useState("");

  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [groupStudents, setGroupStudents] = useState([]);
  const [loadingStudents, setLoadingStudents] = useState(false);

  const [selectedStudentProfile, setSelectedStudentProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  const load = () => fetchGroups().then(setGroups).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await createGroup({ name });
      setName("");
      load();
      notify("success", "Guruh qo'shildi", "Yangi guruh yaratildi.");
    } catch (err) {
      setError(err.message);
      notify("error", "Guruh qo'shilmadi", err.message);
    }
  }

  // navigation: clicking a group should open the group's detail page

  return (
    <main className="dashboard-content">
      <section className="panel neon-panel">
        <h2>Guruh qo'shish</h2>
        <form onSubmit={submit}>
          <label>Guruh nomi<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <button>Saqlash</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel neon-panel">
        <h2>Guruhlar</h2>
        <div className="results-table">
          {groups.map((g) => (
            <div key={g.id} className="result-row clickable" onClick={() => onOpenGroup && onOpenGroup(g.id)}>
              <div>
                <strong>{g.name}</strong>
                <p>{g.student_count} o'quvchi</p>
              </div>
            </div>
          ))}
        </div>

        {selectedStudentProfile && (
          <div className="panel-inner">
            <h3>Profil</h3>
            {loadingProfile ? (
              <p>Yuklanmoqda...</p>
            ) : (
              <div className="profile-card">
                <strong>{selectedStudentProfile.first_name} {selectedStudentProfile.last_name}</strong>
                <p>{selectedStudentProfile.username}</p>
                <p>{selectedStudentProfile.bio}</p>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

function TeacherSubjects({ notify, onOpenSubject }) {
  const [data, setData] = useState(null);
  const [groupId, setGroupId] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [expandedSubjectId, setExpandedSubjectId] = useState(null);
  const load = async () => { try { const d = await fetchTeacherDashboard({ page: 1, pageSize: PAGE_SIZE }); setData(d); if (!groupId && d.groups.length) setGroupId(String(d.groups[0].group.id)); } catch (e) { setError(e.message); } };
  useEffect(() => { load(); }, []);
  async function submit(e) { e.preventDefault(); setError(""); try { await createSubject({ group_id: Number(groupId), name }); setName(""); await load(); notify("success", "Fan qo'shildi", "Fan guruhga biriktirildi."); } catch (err) { setError(err.message); notify("error", "Fan qo'shilmadi", err.message); } }
  const current = data?.groups.find((g) => String(g.group.id) === String(groupId));

  function toggleSubject(id) {
    setExpandedSubjectId((prev) => (prev === id ? null : id));
  }

  return (
    <main className="dashboard-content">
      <section className="panel neon-panel">
        <h2>Fan qo'shish</h2>
        <form onSubmit={submit}>
          <label>Guruh<select value={groupId} onChange={(e) => setGroupId(e.target.value)}>{data?.groups.map((g) => <option key={g.group.id} value={g.group.id}>{g.group.name}</option>)}</select></label>
          <label>Fan nomi<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <button>Saqlash</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel neon-panel">
        <h2>Fanlar</h2>
        <div className="results-table">
          {current?.subjects?.length ? current.subjects.map((s) => (
            <div key={s.id} className="result-row clickable" onClick={() => onOpenSubject && onOpenSubject(s.id)}>
              <div>
                <strong>{s.name}</strong>
                <p>{s.question_count} savol</p>
              </div>
            </div>
          )) : <p className="empty-text">Fanlar topilmadi.</p>}
        </div>
      </section>
    </main>
  );
}


function GroupDetail({ groupId, onBack, onOpenStudent }) {
  const [students, setStudents] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [groupName, setGroupName] = useState("");

  useEffect(() => {
    let mounted = true;
    setLoading(true);

    // Fetch students and also try to resolve the group's name (for header)
    Promise.all([fetchGroupStudents(groupId), fetchGroups()])
      .then(([studentsData, groups]) => {
        if (!mounted) return;
        setStudents(studentsData || []);
        const found = Array.isArray(groups) ? groups.find((g) => String(g.id) === String(groupId)) : null;
        setGroupName(found ? found.name : `Guruh ${groupId}`);
      })
      .catch((e) => { if (mounted) setError(e.message); })
      .finally(() => { if (mounted) setLoading(false); });

    return () => { mounted = false; };
  }, [groupId]);

  return (
    <main className="dashboard-content">
      <header className="topbar"><div><p className="eyebrow">Guruh</p><h1>{groupName || 'Guruh tafsiloti'}</h1></div><button className="ghost-button" onClick={onBack}>Ortga</button></header>
      <section className="panel neon-panel"><h2>O'quvchilar</h2>
        {loading ? (
          <p>Yuklanmoqda...</p>
        ) : students.length ? (
          <div className="results-table">
            {students.map((s, idx) => (
              <div key={s.id} className="result-row clickable" onClick={() => onOpenStudent && onOpenStudent(s.id)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ minWidth: 28, textAlign: 'center', fontWeight: 700 }}>{idx + 1}.</div>
                  <div>
                    <strong>{(s.first_name || s.username) + (s.last_name ? ` ${s.last_name}` : '')}</strong>
                    <p>{s.username}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-text">O'quvchi topilmadi.</p>
        )}
        {error && <p className="error">{error}</p>}
      </section>
    </main>
  );
}


function SubjectDetail({ subjectId, onBack, onOpenQuestion }) {
  const [questions, setQuestions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchSubjectQuestions(subjectId).then((d) => { if (mounted) setQuestions(d || []); }).catch((e) => { if (mounted) setError(e.message); }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [subjectId]);

  return (
    <main className="dashboard-content">
      <header className="topbar"><div><p className="eyebrow">Fan</p><h1>Fan tafsiloti</h1></div><button className="ghost-button" onClick={onBack}>Ortga</button></header>
      <section className="panel neon-panel"><h2>Savollar</h2>
        {loading ? (
          <p>Yuklanmoqda...</p>
        ) : questions.length ? (
          <div className="results-table">
            {questions.map((q) => (
              <div key={q.id} className="result-row clickable" onClick={() => onOpenQuestion && onOpenQuestion(q.id)}>
                <div>
                  <strong>{q.title}</strong>
                  <p>{q.submission_count} topshiriq, o'rtacha {q.average_score}%</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-text">Savollar topilmadi.</p>
        )}
      </section>
    </main>
  );
}


function StudentProfilePage({ userId, onBack }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchUserProfile(userId).then((d) => { if (mounted) setProfile(d); }).catch((e) => { if (mounted) setError(e.message); }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [userId]);

  return (
    <main className="dashboard-content profile-page">
      <header className="topbar"><div><p className="eyebrow">Profil</p><h1>Foydalanuvchi</h1></div><button className="ghost-button" onClick={onBack}>Ortga</button></header>
      <section className="panel neon-panel">{loading ? <p>Yuklanmoqda...</p> : profile ? <div className="profile-card"><strong>{profile.first_name} {profile.last_name}</strong><p>{profile.username}</p><p>{profile.bio}</p></div> : <p className="error">{error || 'Topilmadi'}</p>}</section>
    </main>
  );
}


function QuestionDetail({ questionId, onBack }) {
  const [question, setQuestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchQuestion(questionId).then((d) => { if (mounted) setQuestion(d); }).catch((e) => { if (mounted) setError(e.message); }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [questionId]);

  return (
    <main className="dashboard-content">
      <header className="topbar"><div><p className="eyebrow">Savol</p><h1>{question?.title || 'Savol tafsiloti'}</h1></div><button className="ghost-button" onClick={onBack}>Ortga</button></header>
      <section className="panel neon-panel">
        {loading ? <p>Yuklanmoqda...</p> : question ? (
          <div>
            <h2>{question.title}</h2>
            <p className="meta">{question.subject_name} — {question.submission_count} topshiriq, o'rtacha {question.average_score}%</p>
            <article className="question-text"><pre style={{ whiteSpace: 'pre-wrap' }}>{question.text}</pre></article>
          </div>
        ) : (
          <p className="error">{error || 'Savol topilmadi'}</p>
        )}
      </section>
    </main>
  );
}

function TeacherQuestions({ notify }) {
  const [data, setData] = useState(null); const [groupId, setGroupId] = useState(""); const [draft, setDraft] = useState({ subject_id: "", title: "", text: "", minimum_words: 25 }); const [error, setError] = useState("");
  const load = async () => { try { const d = await fetchTeacherDashboard({ page: 1, pageSize: PAGE_SIZE }); setData(d); if (!groupId && d.groups.length) setGroupId(String(d.groups[0].group.id)); } catch (e) { setError(e.message); } };
  useEffect(() => { load(); }, []);
  const subjects = groupId ? data?.available_subjects.filter((s) => String(s.group_id) === String(groupId)) || [] : [];
  useEffect(() => { if (subjects.length && !draft.subject_id) setDraft((v) => ({ ...v, subject_id: String(subjects[0].id) })); }, [subjects, draft.subject_id]);
  async function submit(e) { e.preventDefault(); setError(""); try { await createQuestion({ subject_id: Number(draft.subject_id), title: draft.title, text: draft.text, minimum_words: Number(draft.minimum_words) }); setDraft((v) => ({ ...v, title: "", text: "" })); await load(); notify("success", "Savol qo'shildi", "Savol fanga biriktirildi."); } catch (err) { setError(err.message); notify("error", "Savol qo'shilmadi", err.message); } }
  const current = data?.groups.find((g) => String(g.group.id) === String(groupId));
  return <main className="dashboard-content"><section className="panel neon-panel"><h2>Savol qo'shish</h2><form onSubmit={submit}><label>Guruh<select value={groupId} onChange={(e) => { setGroupId(e.target.value); setDraft((v) => ({ ...v, subject_id: "" })); }}>{data?.groups.map((g) => <option key={g.group.id} value={g.group.id}>{g.group.name}</option>)}</select></label><label>Fan<select value={draft.subject_id} onChange={(e) => setDraft({ ...draft, subject_id: e.target.value })}>{subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label>Sarlavha<input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} required /></label><label>Savol matni<textarea className="compact-textarea" value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })} required /></label><label>Minimal so'z<input type="number" min="5" value={draft.minimum_words} onChange={(e) => setDraft({ ...draft, minimum_words: e.target.value })} /></label><button disabled={!draft.subject_id}>Saqlash</button></form>{error && <p className="error">{error}</p>}</section><section className="panel neon-panel"><h2>Savollar</h2><div className="results-table">{current?.questions?.length ? current.questions.map((q) => <div key={q.id} className="result-row"><div><strong>{q.title}</strong><p>{q.subject_name}</p><p>{q.submission_count} topshiriq, o'rtacha {q.average_score}%</p></div></div>) : <p className="empty-text">Savollar topilmadi.</p>}</div></section></main>;
}

function TeacherShell({ session, onLogout, setSession, notify }) {
  const [page, setPage] = useState("dashboard");
  const [detailType, setDetailType] = useState(null); // 'group' | 'subject' | 'student'
  const [detailId, setDetailId] = useState(null);

  function openGroup(id) {
    setDetailType("group");
    setDetailId(id);
    setPage("detail");
  }

  function openSubject(id) {
    setDetailType("subject");
    setDetailId(id);
    setPage("detail");
  }

  function openStudentProfilePage(id) {
    setDetailType("student");
    setDetailId(id);
    setPage("detail");
  }

  function openQuestion(id) {
    setDetailType("question");
    setDetailId(id);
    setPage("detail");
  }

  return (
    <main className="dashboard-layout neon-grid teacher-layout">
      <TeacherNav active={page} onNav={setPage} onLogout={onLogout} />
      {page === "dashboard" && <TeacherDashboard session={session} notify={notify} />}
      {page === "groups" && <TeacherGroups notify={notify} onOpenGroup={openGroup} />}
      {page === "subjects" && <TeacherSubjects notify={notify} onOpenSubject={openSubject} />}
      {page === "questions" && <TeacherQuestions notify={notify} />}
      {page === "profile" && <Profile session={session} onBack={() => { setPage("dashboard"); setDetailType(null); setDetailId(null); }} setSession={setSession} notify={notify} />}
      {page === "detail" && detailType === "group" && <GroupDetail groupId={detailId} onBack={() => setPage("groups")} onOpenStudent={(id) => openStudentProfilePage(id)} />}
      {page === "detail" && detailType === "subject" && <SubjectDetail subjectId={detailId} onBack={() => setPage("subjects")} onOpenQuestion={(id) => openQuestion(id)} />}
      {page === "detail" && detailType === "student" && <StudentProfilePage userId={detailId} onBack={() => setPage("groups")} />}
      {page === "detail" && detailType === "question" && <QuestionDetail questionId={detailId} onBack={() => setPage("subjects")} />}
    </main>
  );
}

export default function App() {
  const [session, setSession] = useState(null); const [checking, setChecking] = useState(true); const [showLogin, setShowLogin] = useState(false); const [subjectId, setSubjectId] = useState(""); const [result, setResult] = useState(null); const [studentPage, setStudentPage] = useState("home"); const [toasts, setToasts] = useState([]);
  useEffect(() => { fetchSession().then(setSession).catch(() => clearToken()).finally(() => setChecking(false)); }, []);
  function notify(type, title, message) { const id = `${Date.now()}-${Math.random()}`; setToasts((v) => [...v, { id, type, title, message }]); window.setTimeout(() => setToasts((v) => v.filter((t) => t.id !== id)), 3500); }
  async function onLogout() { try { await logout(); } catch { } finally { clearToken(); setSession(null); setShowLogin(false); setSubjectId(""); setResult(null); setStudentPage("home"); notify("success", "Sessiya yopildi", "Hisobingizdan chiqdingiz."); } }
  if (checking) return <main className="exam-layout neon-grid"><p className="eyebrow">Sessiya tekshirilmoqda...</p></main>;
  return <><Toasts items={toasts} onClose={(id) => setToasts((v) => v.filter((t) => t.id !== id))} />{!session && !showLogin && <Landing onEnter={() => setShowLogin(true)} />}{!session && showLogin && <Login onLogin={(v) => { setSession(v); notify("success", "Kirish muvaffaqiyatli", "Siz tizimga kirdingiz."); }} onBack={() => setShowLogin(false)} />}{session?.role === "teacher" && <TeacherShell session={session} onLogout={onLogout} setSession={setSession} notify={notify} />}{session?.role === "student" && studentPage === "profile" && <Profile session={session} onBack={() => setStudentPage("home")} setSession={setSession} notify={notify} />}{session?.role === "student" && studentPage === "home" && !subjectId && !result && <StudentHome session={session} onStart={setSubjectId} onProfile={() => setStudentPage("profile")} onLogout={onLogout} />}{session?.role === "student" && subjectId && !result && <Exam session={session} subjectId={subjectId} onDone={(v) => { setResult(v); notify("success", "Natija tayyor", "Javobingiz tekshirildi."); }} onBack={() => setSubjectId("")} />}{session?.role === "student" && result && <Result result={result} onRestart={() => { setResult(null); setSubjectId(""); }} onProfile={() => { setResult(null); setSubjectId(""); setStudentPage("profile"); }} onLogout={onLogout} />}</>;
}
