import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

import { createDbConnection } from './db.js';
import { setupRoutes } from './routes.js';
import { setupWebSocket } from './websocket.js';

// Load environment variables from project root
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const envPath = path.resolve(__dirname, '../../../.env');
dotenv.config({ path: envPath });

const PORT = process.env.SERVER_PORT || 3001;
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

// Initialize Express app
const app = express();
const httpServer = createServer(app);

// Initialize Socket.io with CORS
const io = new Server(httpServer, {
  cors: {
    origin: FRONTEND_URL,
    methods: ['GET', 'POST'],
  },
});

// Middleware
app.use(cors({ origin: FRONTEND_URL }));
app.use(express.json());

// Initialize database connection
const db = createDbConnection();

// Setup REST routes
setupRoutes(app, db);

// Setup WebSocket handlers
setupWebSocket(io, db);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Start server
httpServer.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`Accepting connections from: ${FRONTEND_URL}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down...');
  db.close();
  httpServer.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
