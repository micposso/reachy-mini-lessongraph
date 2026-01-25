import {
  getAllLessons,
  getLessonById,
  getAllSessions,
  getSessionById,
  getAllStudents,
  getStudentSessions,
  getGraphState,
  getDashboardStats,
} from './db.js';

/**
 * Setup REST API routes.
 */
export function setupRoutes(app, db) {
  // ============================================
  // Dashboard Overview
  // ============================================

  /**
   * GET /api/dashboard
   * Get dashboard overview statistics.
   */
  app.get('/api/dashboard', (req, res) => {
    try {
      const stats = getDashboardStats(db);
      res.json(stats);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      res.status(500).json({ error: 'Failed to fetch dashboard stats' });
    }
  });

  // ============================================
  // Lessons
  // ============================================

  /**
   * GET /api/lessons
   * Get all lessons.
   */
  app.get('/api/lessons', (req, res) => {
    try {
      const lessons = getAllLessons(db);
      res.json(lessons);
    } catch (error) {
      console.error('Error fetching lessons:', error);
      res.status(500).json({ error: 'Failed to fetch lessons' });
    }
  });

  /**
   * GET /api/lessons/:id
   * Get a specific lesson by ID.
   */
  app.get('/api/lessons/:id', (req, res) => {
    try {
      const lesson = getLessonById(db, req.params.id);
      if (!lesson) {
        return res.status(404).json({ error: 'Lesson not found' });
      }
      res.json(lesson);
    } catch (error) {
      console.error('Error fetching lesson:', error);
      res.status(500).json({ error: 'Failed to fetch lesson' });
    }
  });

  // ============================================
  // Sessions
  // ============================================

  /**
   * GET /api/sessions
   * Get all sessions.
   */
  app.get('/api/sessions', (req, res) => {
    try {
      const sessions = getAllSessions(db);
      res.json(sessions);
    } catch (error) {
      console.error('Error fetching sessions:', error);
      res.status(500).json({ error: 'Failed to fetch sessions' });
    }
  });

  /**
   * GET /api/sessions/:id
   * Get a specific session by ID.
   */
  app.get('/api/sessions/:id', (req, res) => {
    try {
      const session = getSessionById(db, req.params.id);
      if (!session) {
        return res.status(404).json({ error: 'Session not found' });
      }
      res.json(session);
    } catch (error) {
      console.error('Error fetching session:', error);
      res.status(500).json({ error: 'Failed to fetch session' });
    }
  });

  /**
   * GET /api/sessions/:id/state
   * Get the reconstructed graph state for a session.
   */
  app.get('/api/sessions/:id/state', (req, res) => {
    try {
      const state = getGraphState(db, req.params.id);
      if (!state) {
        return res.status(404).json({ error: 'Session not found' });
      }
      res.json(state);
    } catch (error) {
      console.error('Error fetching graph state:', error);
      res.status(500).json({ error: 'Failed to fetch graph state' });
    }
  });

  // ============================================
  // Students
  // ============================================

  /**
   * GET /api/students
   * Get all students with aggregated stats.
   */
  app.get('/api/students', (req, res) => {
    try {
      const students = getAllStudents(db);
      res.json(students);
    } catch (error) {
      console.error('Error fetching students:', error);
      res.status(500).json({ error: 'Failed to fetch students' });
    }
  });

  /**
   * GET /api/students/:id/sessions
   * Get all sessions for a specific student.
   */
  app.get('/api/students/:id/sessions', (req, res) => {
    try {
      const sessions = getStudentSessions(db, req.params.id);
      res.json(sessions);
    } catch (error) {
      console.error('Error fetching student sessions:', error);
      res.status(500).json({ error: 'Failed to fetch student sessions' });
    }
  });

  // ============================================
  // Graph State (for active monitoring)
  // ============================================

  /**
   * GET /api/graph/active
   * Get all active (incomplete) sessions with their graph states.
   */
  app.get('/api/graph/active', (req, res) => {
    try {
      const sessions = getAllSessions(db);
      const activeSessions = sessions
        .filter(s => s.score === null)
        .map(s => getGraphState(db, s.id))
        .filter(Boolean);
      res.json(activeSessions);
    } catch (error) {
      console.error('Error fetching active sessions:', error);
      res.status(500).json({ error: 'Failed to fetch active sessions' });
    }
  });
}
