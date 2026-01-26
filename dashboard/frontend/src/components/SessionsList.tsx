import { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  LinearProgress,
  Divider,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import QuizIcon from '@mui/icons-material/Quiz';
import GradingIcon from '@mui/icons-material/Grading';
import SummarizeIcon from '@mui/icons-material/Summarize';
import { api } from '../api';
import type { Session, GraphState, TranscriptEntry } from '../types';

function TranscriptMessage({ entry }: { entry: TranscriptEntry }) {
  const getIcon = () => {
    switch (entry.role) {
      case 'teacher':
        return <SmartToyIcon sx={{ color: '#1976d2' }} />;
      case 'student':
        return <PersonIcon sx={{ color: '#2e7d32' }} />;
      case 'quiz_agent':
        return <QuizIcon sx={{ color: '#ed6c02' }} />;
      case 'grader_agent':
        return <GradingIcon sx={{ color: '#9c27b0' }} />;
      case 'summary_agent':
        return <SummarizeIcon sx={{ color: '#d32f2f' }} />;
      default:
        return <SmartToyIcon />;
    }
  };

  const getContent = () => {
    if (entry.text) return entry.text;
    if (entry.question) return `Q: ${entry.question}`;
    if (entry.result) return `Score: ${entry.result.total_score}/${entry.result.max_score}`;
    if (entry.summary) return `Summary generated for ${entry.summary.lesson_title}`;
    return JSON.stringify(entry);
  };

  const isBot = entry.role !== 'student';

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        mb: 2,
        flexDirection: isBot ? 'row' : 'row-reverse',
      }}
    >
      <Box sx={{ mx: 1 }}>{getIcon()}</Box>
      <Paper
        sx={{
          p: 2,
          maxWidth: '70%',
          bgcolor: isBot ? 'grey.100' : 'primary.light',
          color: isBot ? 'text.primary' : 'primary.contrastText',
        }}
      >
        <Typography variant="caption" color={isBot ? 'text.secondary' : 'inherit'}>
          {entry.role}
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
          {getContent()}
        </Typography>
      </Paper>
    </Box>
  );
}

function SessionDetailDialog({
  sessionId,
  open,
  onClose,
}: {
  sessionId: string | null;
  open: boolean;
  onClose: () => void;
}) {
  const [state, setState] = useState<GraphState | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && sessionId) {
      setLoading(true);
      api
        .getSessionState(sessionId)
        .then(setState)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [open, sessionId]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Session Details
        {state && (
          <Chip
            label={state.isComplete ? 'Completed' : state.inQuiz ? 'In Quiz' : 'Teaching'}
            color={state.isComplete ? 'success' : 'info'}
            size="small"
            sx={{ ml: 2 }}
          />
        )}
      </DialogTitle>
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : state ? (
          <Box>
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Lesson
              </Typography>
              <Typography variant="h6">{state.lessonTitle}</Typography>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Student
              </Typography>
              <Typography>{state.studentId}</Typography>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                Progress
              </Typography>
              <LinearProgress
                variant="determinate"
                value={state.progressPercent}
                sx={{ height: 10, borderRadius: 1 }}
              />
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                Segment {state.segmentIndex} of {state.totalSegments} ({state.progressPercent}%)
              </Typography>
            </Box>

            {state.score !== null && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Quiz Score
                </Typography>
                <Typography variant="h5">
                  {state.score}/{state.scoreMax} ({state.scorePercent}%)
                </Typography>
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" sx={{ mb: 2 }}>
              Transcript ({state.transcriptLength} messages)
            </Typography>

            <Box sx={{ maxHeight: 400, overflowY: 'auto' }}>
              {state.transcript.length === 0 ? (
                <Typography color="text.secondary">No transcript yet</Typography>
              ) : (
                state.transcript.map((entry, i) => (
                  <TranscriptMessage key={i} entry={entry} />
                ))
              )}
            </Box>
          </Box>
        ) : (
          <Alert severity="error">Failed to load session details</Alert>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function SessionsList() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSessions() {
      try {
        const data = await api.getSessions();
        setSessions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch sessions');
      } finally {
        setLoading(false);
      }
    }

    fetchSessions();
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Sessions
      </Typography>

      {sessions.length === 0 ? (
        <Alert severity="info">
          No sessions found. Run a teaching session to see data here.
        </Alert>
      ) : (
        <Card>
          <CardContent>
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Student</TableCell>
                    <TableCell>Lesson</TableCell>
                    <TableCell align="center">Progress</TableCell>
                    <TableCell align="center">Score</TableCell>
                    <TableCell align="right">Started</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell>{session.studentId}</TableCell>
                      <TableCell>{session.lessonTitle || 'Unknown'}</TableCell>
                      <TableCell align="center">
                        <Chip
                          label={`Segment ${session.segmentIndex}`}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="center">
                        {session.score !== null ? (
                          <Chip
                            label={`${session.score}/${session.scoreMax}`}
                            color="success"
                            size="small"
                          />
                        ) : (
                          <Chip label="In Progress" color="info" size="small" />
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {new Date(session.startedAt).toLocaleString()}
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          onClick={() => setSelectedSession(session.id)}
                        >
                          <VisibilityIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      <SessionDetailDialog
        sessionId={selectedSession}
        open={!!selectedSession}
        onClose={() => setSelectedSession(null)}
      />
    </Box>
  );
}
