# REACHY-TEACHER

LangGraph-orchestrated multi-agent tutoring pipeline for the Reachy Mini humanoid robot. A "robotic learning OS" that delivers interactive lessons through stateful, durable orchestration.

## Quick Reference

```bash
# Activate environment
.venv\Scripts\activate.bat  # Windows
source .venv/bin/activate   # Linux/Mac

# Install dependencies
uv sync

# Run commands (always use --env-file .env)
uv run --env-file .env python -m reachy_teacher.rag_smoke          # Ingest docs to vector store
uv run --env-file .env python -m reachy_teacher.planner_only_graph # Generate lesson plan
uv run --env-file .env python -m reachy_teacher.teach_graph        # Run full teaching session
python -m reachy_teacher.db                                        # List students/sessions

# Reachy daemon
uv run reachy-mini-daemon       # Real robot
uv run reachy-mini-daemon --sim # Simulation mode
```

## Project Structure

```
src/reachy_teacher/
├── teach_graph.py          # Main teaching pipeline (LangGraph)
├── planner_only_graph.py   # Lesson planning workflow
├── state.py                # Pydantic models & TypedDict definitions
├── document_loader.py      # PDF/Markdown lesson loading
├── rag_smoke.py            # RAG vector store setup
├── db.py                   # SQLAlchemy ORM (Lesson, Session models)
├── io/                     # Robot abstraction layer
│   ├── robot_factory.py    # get_robot() - returns mock or reachy based on env
│   ├── robot_mock.py       # Mock implementation for testing
│   └── robot_reachy_media.py # Real Reachy Mini with TTS/STT
└── agents/                 # LLM agents
    ├── quiz_agent.py       # Quiz generation
    ├── grader_agent.py     # Answer grading & scoring
    └── summary_agent.py    # Lesson summary generation

dashboard/
├── frontend/               # React + Vite + TypeScript
└── server/                 # Node.js + Express + Socket.io API server

lessons/                    # Course content (PDF/Markdown files)
```

## Key Technologies

- **LangGraph** - Stateful graph orchestration for multi-agent workflows
- **LangChain + Chroma** - RAG document retrieval
- **OpenAI** - GPT-4 (LLM), TTS, STT, Embeddings
- **SQLAlchemy + SQLite** - Persistence (reachy_teacher.sqlite)
- **Reachy Mini SDK** - Robot control
- **uv** - Python package manager
- **Express + Socket.io** - Dashboard API server
- **React + Vite** - Dashboard frontend

## Environment Variables

Required in `.env`:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
ROBOT_BACKEND=mock          # "mock" or "reachy"
```

Optional:
```env
OPENAI_EMBED_MODEL=text-embedding-3-large
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
SQLITE_PATH=reachy_teacher.sqlite
CHROMA_DIR=./chroma_index
STUDENT_ID=default_student

# Dashboard server
SERVER_PORT=3001
FRONTEND_URL=http://localhost:5173
```

## Teaching Pipeline Flow

```
load_lesson → ensure_session → introduce → teach (loop) → quiz → grade → summarize → persist
```

The graph maintains `GraphState` throughout and persists to SQLite after each step, allowing session resumption.

## Robot Capabilities

**Emotions:** happy, excited, encouraging, curious, thinking, sad, serious, neutral
**Motions:** nod, shake, celebrate, think, encourage, look_at_student, idle

```python
robot = get_robot()
robot.say("Hello")
robot.set_emotion("happy")
robot.do_motion("nod")
response = robot.ask_and_listen_text("Question?", record_seconds=12.0)
```

## Testing

```bash
python scripts/reachy_robot_test.py   # Full integration test
python scripts/reachy_voice_smoke.py  # TTS/STT validation
python scripts/reachy_connect_smoke.py # Connection test
```

## Adding Lessons

1. Create folder: `lessons/<course-name>/`
2. Add PDF or Markdown files
3. Run `uv run --env-file .env python -m reachy_teacher.rag_smoke` to ingest
4. Run `uv run --env-file .env python -m reachy_teacher.planner_only_graph` to create plan

## Dashboard Server

The dashboard server provides REST API and WebSocket endpoints for the React frontend.

### Running the Server

```bash
cd dashboard/server
npm install
npm run dev    # Development with auto-reload
npm start      # Production
```

Server runs on `http://localhost:3001` (configurable via `SERVER_PORT` env var).

### REST API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/dashboard` | Overview stats (lessons, sessions, students, avg score) |
| `GET /api/lessons` | All lessons with plans |
| `GET /api/lessons/:id` | Single lesson |
| `GET /api/sessions` | All sessions |
| `GET /api/sessions/:id` | Single session with transcript |
| `GET /api/sessions/:id/state` | Reconstructed graph state |
| `GET /api/students` | All students with stats |
| `GET /api/students/:id/sessions` | Sessions for a student |
| `GET /api/graph/active` | All active (incomplete) sessions |

### WebSocket Events

Connect to `ws://localhost:3001` for real-time updates:

| Event | Direction | Description |
|-------|-----------|-------------|
| `dashboard:update` | Server → Client | Real-time dashboard stats |
| `session:watch` | Client → Server | Subscribe to session updates |
| `session:unwatch` | Client → Server | Unsubscribe from session |
| `session:update` | Server → Client | Session state changes |
| `session:new` | Server → Client | New session started |
| `sessions:active` | Client → Server | Request all active sessions |

### Testing the API

```bash
curl http://localhost:3001/health
curl http://localhost:3001/api/dashboard
curl http://localhost:3001/api/lessons
curl http://localhost:3001/api/sessions
curl http://localhost:3001/api/students
```
