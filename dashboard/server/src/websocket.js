import { getAllSessions, getGraphState, getDashboardStats } from './db.js';

// Store for tracking watched sessions
const watchers = new Map();

// Polling interval for database changes (ms)
const POLL_INTERVAL = 2000;

/**
 * Setup WebSocket handlers for real-time updates.
 */
export function setupWebSocket(io, db) {
  // Track last known state for change detection
  let lastStates = new Map();
  let lastDashboardStats = null;

  /**
   * Poll database for changes and emit updates.
   */
  function pollForChanges() {
    try {
      // Check dashboard stats
      const currentStats = getDashboardStats(db);
      const statsJson = JSON.stringify(currentStats);

      if (lastDashboardStats !== statsJson) {
        lastDashboardStats = statsJson;
        io.emit('dashboard:update', currentStats);
      }

      // Check each watched session for changes
      for (const [sessionId, sockets] of watchers.entries()) {
        if (sockets.size === 0) continue;

        const state = getGraphState(db, sessionId);
        if (!state) continue;

        const stateJson = JSON.stringify(state);
        const lastState = lastStates.get(sessionId);

        if (lastState !== stateJson) {
          lastStates.set(sessionId, stateJson);

          // Emit to all watchers of this session
          for (const socketId of sockets) {
            const socket = io.sockets.sockets.get(socketId);
            if (socket) {
              socket.emit('session:update', state);
            }
          }
        }
      }

      // Check for new sessions
      const sessions = getAllSessions(db);
      const activeSessions = sessions.filter(s => s.score === null);

      for (const session of activeSessions) {
        const state = getGraphState(db, session.id);
        if (!state) continue;

        const stateJson = JSON.stringify(state);
        const lastState = lastStates.get(session.id);

        if (!lastState) {
          lastStates.set(session.id, stateJson);
          io.emit('session:new', state);
        }
      }
    } catch (error) {
      console.error('Error polling for changes:', error);
    }
  }

  // Start polling
  const pollInterval = setInterval(pollForChanges, POLL_INTERVAL);

  io.on('connection', (socket) => {
    console.log(`Client connected: ${socket.id}`);

    // Send initial dashboard stats
    try {
      const stats = getDashboardStats(db);
      socket.emit('dashboard:update', stats);
    } catch (error) {
      console.error('Error sending initial stats:', error);
    }

    /**
     * Subscribe to a specific session's updates.
     */
    socket.on('session:watch', (sessionId) => {
      console.log(`Client ${socket.id} watching session: ${sessionId}`);

      // Add to watchers
      if (!watchers.has(sessionId)) {
        watchers.set(sessionId, new Set());
      }
      watchers.get(sessionId).add(socket.id);

      // Send current state immediately
      try {
        const state = getGraphState(db, sessionId);
        if (state) {
          socket.emit('session:update', state);
        } else {
          socket.emit('session:error', { sessionId, error: 'Session not found' });
        }
      } catch (error) {
        socket.emit('session:error', { sessionId, error: error.message });
      }
    });

    /**
     * Unsubscribe from a session's updates.
     */
    socket.on('session:unwatch', (sessionId) => {
      console.log(`Client ${socket.id} unwatching session: ${sessionId}`);

      if (watchers.has(sessionId)) {
        watchers.get(sessionId).delete(socket.id);
      }
    });

    /**
     * Request all active sessions.
     */
    socket.on('sessions:active', () => {
      try {
        const sessions = getAllSessions(db);
        const activeSessions = sessions
          .filter(s => s.score === null)
          .map(s => getGraphState(db, s.id))
          .filter(Boolean);
        socket.emit('sessions:active', activeSessions);
      } catch (error) {
        socket.emit('sessions:error', { error: error.message });
      }
    });

    /**
     * Handle disconnection.
     */
    socket.on('disconnect', () => {
      console.log(`Client disconnected: ${socket.id}`);

      // Remove from all watcher lists
      for (const [sessionId, sockets] of watchers.entries()) {
        sockets.delete(socket.id);
        if (sockets.size === 0) {
          watchers.delete(sessionId);
        }
      }
    });
  });

  // Cleanup on server shutdown
  return () => {
    clearInterval(pollInterval);
  };
}
