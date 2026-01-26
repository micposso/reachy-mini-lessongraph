import type {
  DashboardStats,
  Lesson,
  Session,
  Student,
  GraphState,
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001';

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const api = {
  // Dashboard
  getDashboard: () => fetchJson<DashboardStats>('/api/dashboard'),

  // Lessons
  getLessons: () => fetchJson<Lesson[]>('/api/lessons'),
  getLesson: (id: string) => fetchJson<Lesson>(`/api/lessons/${id}`),

  // Sessions
  getSessions: () => fetchJson<Session[]>('/api/sessions'),
  getSession: (id: string) => fetchJson<Session>(`/api/sessions/${id}`),
  getSessionState: (id: string) => fetchJson<GraphState>(`/api/sessions/${id}/state`),
  getActiveSessions: () => fetchJson<GraphState[]>('/api/graph/active'),

  // Students
  getStudents: () => fetchJson<Student[]>('/api/students'),
  getStudentSessions: (id: string) => fetchJson<Session[]>(`/api/students/${id}/sessions`),

  // Health
  getHealth: () => fetchJson<{ status: string; timestamp: string }>('/health'),
};
