// API Response Types

export interface DashboardStats {
  totalLessons: number;
  totalSessions: number;
  totalStudents: number;
  completedSessions: number;
  averageScore: number | null;
  recentSessions: RecentSession[];
}

export interface RecentSession {
  id: string;
  studentId: string;
  lessonTitle: string;
  startedAt: string;
  score: number | null;
  scoreMax: number | null;
}

export interface PlanSegment {
  title: string;
  duration_sec: number;
  script: string;
  check_question: string;
  emotion: string;
  motion: string;
  sources: string[];
}

export interface LessonPlan {
  lesson_id: string;
  title: string;
  objectives: string[];
  segments: PlanSegment[];
  next_lesson_hint: string;
}

export interface Lesson {
  id: string;
  title: string;
  plan: LessonPlan;
  createdAt: string;
}

export interface TranscriptEntry {
  role: string;
  text?: string;
  question?: string;
  sources?: string[];
  result?: QuizResult;
  summary?: LessonSummary;
}

export interface Session {
  id: string;
  studentId: string;
  lessonId: string;
  lessonTitle: string;
  segmentIndex: number;
  transcript: TranscriptEntry[];
  startedAt: string;
  endedAt: string | null;
  score: number | null;
  scoreMax: number | null;
}

export interface Student {
  studentId: string;
  sessionCount: number;
  bestScore: number | null;
  scoreMax: number | null;
  lastSession: string;
}

export interface GraphState {
  sessionId: string;
  studentId: string;
  lessonId: string;
  lessonTitle: string;
  currentNode: string;
  segmentIndex: number;
  totalSegments: number;
  progressPercent: number;
  lessonPlan: LessonPlan | null;
  currentSegment: PlanSegment | null;
  transcript: TranscriptEntry[];
  transcriptLength: number;
  score: number | null;
  scoreMax: number | null;
  scorePercent: number | null;
  startedAt: string;
  endedAt: string | null;
  isComplete: boolean;
  inQuiz: boolean;
}

export interface QuizResult {
  total_score: number;
  max_score: number;
  per_question: Array<{
    question: string;
    student_answer: string;
    score: number;
    feedback: string;
  }>;
  feedback: string;
}

export interface LessonSummary {
  lesson_id: string;
  lesson_title: string;
  student_id: string;
  session_id: string;
  duration_minutes: number;
  key_takeaways: string[];
  vocabulary: Array<{ term: string; definition: string }>;
  strengths: string[];
  improvements: string[];
  recommended_next_step: string;
  score: number | null;
  score_max: number | null;
}
