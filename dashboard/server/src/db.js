import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Create a connection to the SQLite database.
 * Uses SQLITE_PATH from env or defaults to project root.
 */
export function createDbConnection() {
  const sqlitePath = process.env.SQLITE_PATH || 'reachy_teacher.sqlite';

  // Resolve path relative to project root (3 levels up from src/)
  const dbPath = path.isAbsolute(sqlitePath)
    ? sqlitePath
    : path.resolve(__dirname, '../../..', sqlitePath);

  console.log(`Connecting to database: ${dbPath}`);

  const db = new Database(dbPath, { readonly: true });

  // Enable foreign keys
  db.pragma('foreign_keys = ON');

  return db;
}

/**
 * Get all lessons from the database.
 */
export function getAllLessons(db) {
  const stmt = db.prepare(`
    SELECT id, title, plan_json, created_at
    FROM lessons
    ORDER BY created_at DESC
  `);

  return stmt.all().map(row => ({
    id: row.id,
    title: row.title,
    plan: JSON.parse(row.plan_json),
    createdAt: row.created_at,
  }));
}

/**
 * Get a single lesson by ID.
 */
export function getLessonById(db, lessonId) {
  const stmt = db.prepare(`
    SELECT id, title, plan_json, created_at
    FROM lessons
    WHERE id = ?
  `);

  const row = stmt.get(lessonId);
  if (!row) return null;

  return {
    id: row.id,
    title: row.title,
    plan: JSON.parse(row.plan_json),
    createdAt: row.created_at,
  };
}

/**
 * Get all sessions from the database.
 */
export function getAllSessions(db) {
  const stmt = db.prepare(`
    SELECT
      s.id,
      s.student_id,
      s.lesson_id,
      s.segment_index,
      s.transcript_json,
      s.started_at,
      s.ended_at,
      s.score,
      s.score_max,
      l.title as lesson_title
    FROM sessions s
    LEFT JOIN lessons l ON s.lesson_id = l.id
    ORDER BY s.started_at DESC
  `);

  return stmt.all().map(row => ({
    id: row.id,
    studentId: row.student_id,
    lessonId: row.lesson_id,
    lessonTitle: row.lesson_title,
    segmentIndex: row.segment_index,
    transcript: JSON.parse(row.transcript_json || '[]'),
    startedAt: row.started_at,
    endedAt: row.ended_at,
    score: row.score,
    scoreMax: row.score_max,
  }));
}

/**
 * Get a single session by ID.
 */
export function getSessionById(db, sessionId) {
  const stmt = db.prepare(`
    SELECT
      s.id,
      s.student_id,
      s.lesson_id,
      s.segment_index,
      s.transcript_json,
      s.started_at,
      s.ended_at,
      s.score,
      s.score_max,
      l.title as lesson_title,
      l.plan_json
    FROM sessions s
    LEFT JOIN lessons l ON s.lesson_id = l.id
    WHERE s.id = ?
  `);

  const row = stmt.get(sessionId);
  if (!row) return null;

  return {
    id: row.id,
    studentId: row.student_id,
    lessonId: row.lesson_id,
    lessonTitle: row.lesson_title,
    lessonPlan: row.plan_json ? JSON.parse(row.plan_json) : null,
    segmentIndex: row.segment_index,
    transcript: JSON.parse(row.transcript_json || '[]'),
    startedAt: row.started_at,
    endedAt: row.ended_at,
    score: row.score,
    scoreMax: row.score_max,
  };
}

/**
 * Get all students with aggregated stats.
 */
export function getAllStudents(db) {
  const stmt = db.prepare(`
    SELECT
      student_id,
      COUNT(id) as session_count,
      MAX(score) as best_score,
      MAX(score_max) as score_max,
      MAX(started_at) as last_session
    FROM sessions
    GROUP BY student_id
    ORDER BY student_id
  `);

  return stmt.all().map(row => ({
    studentId: row.student_id,
    sessionCount: row.session_count,
    bestScore: row.best_score,
    scoreMax: row.score_max,
    lastSession: row.last_session,
  }));
}

/**
 * Get sessions for a specific student.
 */
export function getStudentSessions(db, studentId) {
  const stmt = db.prepare(`
    SELECT
      s.id,
      s.student_id,
      s.lesson_id,
      s.segment_index,
      s.transcript_json,
      s.started_at,
      s.ended_at,
      s.score,
      s.score_max,
      l.title as lesson_title
    FROM sessions s
    LEFT JOIN lessons l ON s.lesson_id = l.id
    WHERE s.student_id = ?
    ORDER BY s.started_at DESC
  `);

  return stmt.all(studentId).map(row => ({
    id: row.id,
    studentId: row.student_id,
    lessonId: row.lesson_id,
    lessonTitle: row.lesson_title,
    segmentIndex: row.segment_index,
    transcript: JSON.parse(row.transcript_json || '[]'),
    startedAt: row.started_at,
    endedAt: row.ended_at,
    score: row.score,
    scoreMax: row.score_max,
  }));
}

/**
 * Get current graph state for a session (reconstructed from DB).
 */
export function getGraphState(db, sessionId) {
  const session = getSessionById(db, sessionId);
  if (!session) return null;

  const totalSegments = session.lessonPlan?.segments?.length || 0;
  const isComplete = session.score !== null;
  const inQuiz = session.segmentIndex >= totalSegments && !isComplete;

  return {
    sessionId: session.id,
    studentId: session.studentId,
    lessonId: session.lessonId,
    lessonTitle: session.lessonTitle,

    // Current progress
    currentNode: isComplete ? 'complete' : inQuiz ? 'quiz' : 'teach',
    segmentIndex: session.segmentIndex,
    totalSegments,
    progressPercent: totalSegments > 0
      ? Math.round((session.segmentIndex / totalSegments) * 100)
      : 0,

    // Lesson plan details
    lessonPlan: session.lessonPlan,
    currentSegment: session.lessonPlan?.segments?.[session.segmentIndex] || null,

    // Transcript and interactions
    transcript: session.transcript,
    transcriptLength: session.transcript.length,

    // Quiz results
    score: session.score,
    scoreMax: session.scoreMax,
    scorePercent: session.scoreMax
      ? Math.round((session.score / session.scoreMax) * 100)
      : null,

    // Timestamps
    startedAt: session.startedAt,
    endedAt: session.endedAt,

    // Status flags
    isComplete,
    inQuiz,
  };
}

/**
 * Get dashboard overview statistics.
 */
export function getDashboardStats(db) {
  const lessonCount = db.prepare('SELECT COUNT(*) as count FROM lessons').get();
  const sessionCount = db.prepare('SELECT COUNT(*) as count FROM sessions').get();
  const studentCount = db.prepare('SELECT COUNT(DISTINCT student_id) as count FROM sessions').get();
  const completedCount = db.prepare('SELECT COUNT(*) as count FROM sessions WHERE score IS NOT NULL').get();

  const avgScore = db.prepare(`
    SELECT AVG(CAST(score AS FLOAT) / CAST(score_max AS FLOAT) * 100) as avg
    FROM sessions
    WHERE score IS NOT NULL AND score_max > 0
  `).get();

  const recentSessions = db.prepare(`
    SELECT
      s.id,
      s.student_id,
      s.started_at,
      s.score,
      s.score_max,
      l.title as lesson_title
    FROM sessions s
    LEFT JOIN lessons l ON s.lesson_id = l.id
    ORDER BY s.started_at DESC
    LIMIT 5
  `).all();

  return {
    totalLessons: lessonCount.count,
    totalSessions: sessionCount.count,
    totalStudents: studentCount.count,
    completedSessions: completedCount.count,
    averageScore: avgScore.avg ? Math.round(avgScore.avg) : null,
    recentSessions: recentSessions.map(row => ({
      id: row.id,
      studentId: row.student_id,
      lessonTitle: row.lesson_title,
      startedAt: row.started_at,
      score: row.score,
      scoreMax: row.score_max,
    })),
  };
}
