const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const SESSION_KEY = "intellicheck-session-token";

export function saveToken(token) {
  localStorage.setItem(SESSION_KEY, token);
}

export function readToken() {
  return localStorage.getItem(SESSION_KEY);
}

export function clearToken() {
  localStorage.removeItem(SESSION_KEY);
}

async function request(path, options = {}) {
  const token = options.token ?? readToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "So'rov bajarilmadi");
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function loginStudent(payload) {
  const session = await request("/login", {
    method: "POST",
    body: JSON.stringify(payload),
    token: null,
  });
  saveToken(session.access_token);
  return session;
}

export function logout() {
  return request("/logout", {
    method: "POST",
  });
}

export function fetchSession() {
  return request("/me");
}

export function fetchGroups() {
  return request("/groups", { token: null });
}

export function fetchStudentSubjects() {
  return request("/student/subjects");
}

export function fetchRandomQuestion(subjectId) {
  return request(`/questions/random?subject_id=${subjectId}`);
}

export function submitAnswer(payload) {
  return request("/submit-answer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchTeacherDashboard(filters = {}) {
  const params = new URLSearchParams();
  if (filters.groupId) {
    params.set("group_id", filters.groupId);
  }
  if (filters.subjectId) {
    params.set("subject_id", filters.subjectId);
  }
  if (filters.studentQuery) {
    params.set("student_query", filters.studentQuery);
  }
  if (filters.scoreRange) {
    params.set("score_range", filters.scoreRange);
  }
  if (filters.aiFlag) {
    params.set("ai_flag", filters.aiFlag);
  }
  if (filters.page) {
    params.set("page", filters.page);
  }
  if (filters.pageSize) {
    params.set("page_size", filters.pageSize);
  }
  if (filters.resultsPage) {
    params.set("results_page", filters.resultsPage);
  }
  if (filters.resultsPageSize) {
    params.set("results_page_size", filters.resultsPageSize);
  }
  const query = params.toString();
  return request(`/teacher/dashboard${query ? `?${query}` : ""}`);
}

export function fetchGroupStudents(groupId) {
  return request(`/teacher/groups/${groupId}/students`);
}

export function fetchUserProfile(userId) {
  return request(`/teacher/users/${userId}`);
}

export function fetchSubjectQuestions(subjectId) {
  return request(`/teacher/subjects/${subjectId}/questions`);
}

export function fetchQuestion(questionId) {
  return request(`/teacher/questions/${questionId}`);
}

export function createGroup(payload) {
  return request("/teacher/groups", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createSubject(payload) {
  return request("/teacher/subjects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createQuestion(payload) {
  return request("/teacher/questions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resetStatistics() {
  return request("/teacher/reset-statistics", {
    method: "POST",
  });
}

export function fetchProfile() {
  return request("/profile");
}

export function updateProfile(payload) {
  return request("/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updatePassword(payload) {
  return request("/profile/password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
