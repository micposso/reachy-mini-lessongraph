import { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { api } from '../api';
import type { GraphState } from '../types';

function ActiveSessionCard({ state }: { state: GraphState }) {
  const getStatusColor = () => {
    if (state.isComplete) return 'success';
    if (state.inQuiz) return 'warning';
    return 'info';
  };

  const getStatusLabel = () => {
    if (state.isComplete) return 'Completed';
    if (state.inQuiz) return 'Quiz';
    return `Teaching: ${state.currentSegment?.title || 'Loading...'}`;
  };

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <SmartToyIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            {state.studentId}
          </Typography>
          <Chip label={getStatusLabel()} color={getStatusColor()} size="small" />
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {state.lessonTitle}
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="body2">Progress</Typography>
            <Typography variant="body2">
              {state.segmentIndex}/{state.totalSegments}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={state.progressPercent}
            sx={{ height: 8, borderRadius: 1 }}
          />
        </Box>

        {state.currentSegment && !state.isComplete && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Current Segment
            </Typography>
            <Typography variant="body2">{state.currentSegment.title}</Typography>
            <Box sx={{ mt: 1 }}>
              <Chip
                label={state.currentSegment.emotion}
                size="small"
                sx={{ mr: 0.5 }}
              />
              <Chip
                label={state.currentSegment.motion}
                size="small"
                variant="outlined"
              />
            </Box>
          </Box>
        )}

        {state.score !== null && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              Final Score
            </Typography>
            <Typography variant="h5" color={state.scorePercent && state.scorePercent >= 80 ? 'success.main' : 'text.primary'}>
              {state.score}/{state.scoreMax} ({state.scorePercent}%)
            </Typography>
          </Box>
        )}

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          Started: {new Date(state.startedAt).toLocaleString()}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function ActiveSessions() {
  const [sessions, setSessions] = useState<GraphState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchActiveSessions() {
      try {
        const data = await api.getActiveSessions();
        setSessions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch active sessions');
      } finally {
        setLoading(false);
      }
    }

    fetchActiveSessions();
    const interval = setInterval(fetchActiveSessions, 2000);
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
        Active Sessions
      </Typography>

      {sessions.length === 0 ? (
        <Alert severity="info">
          No active sessions. Start a teaching session to monitor it here in real-time.
        </Alert>
      ) : (
        <Grid container spacing={3}>
          {sessions.map((state) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={state.sessionId}>
              <ActiveSessionCard state={state} />
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
