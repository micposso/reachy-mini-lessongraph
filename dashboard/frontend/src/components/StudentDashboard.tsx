import { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Avatar,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SchoolIcon from '@mui/icons-material/School';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';
import PersonIcon from '@mui/icons-material/Person';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import { api } from '../api';
import type { GraphState, TranscriptEntry } from '../types';

function CaptionDisplay({ transcript }: { transcript: TranscriptEntry[] }) {
  // Get the last few messages for captions
  const recentMessages = transcript.slice(-3);
  const lastTeacherMessage = [...transcript]
    .reverse()
    .find((entry) => entry.role === 'teacher' && entry.text);

  return (
    <Card sx={{ height: '100%', bgcolor: '#1a1a2e', color: 'white' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <VolumeUpIcon sx={{ mr: 1, color: '#4fc3f7' }} />
          <Typography variant="h6">Reachy Says</Typography>
        </Box>

        <Box
          sx={{
            minHeight: 120,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {lastTeacherMessage ? (
            <Typography
              variant="h5"
              sx={{
                textAlign: 'center',
                fontStyle: 'italic',
                lineHeight: 1.6,
                px: 2,
              }}
            >
              "{lastTeacherMessage.text && lastTeacherMessage.text.length > 200
                ? lastTeacherMessage.text.substring(0, 200) + '...'
                : lastTeacherMessage.text}"
            </Typography>
          ) : (
            <Typography variant="body1" color="grey.500">
              Waiting for Reachy to speak...
            </Typography>
          )}
        </Box>

        <Box sx={{ mt: 2 }}>
          {recentMessages.map((entry, i) => (
            <Chip
              key={i}
              label={entry.role}
              size="small"
              sx={{
                mr: 0.5,
                mb: 0.5,
                bgcolor: entry.role === 'teacher' ? '#4fc3f7' : '#81c784',
                color: 'black',
              }}
            />
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}

function LessonProgressStepper({ state }: { state: GraphState }) {
  const segments = state.lessonPlan?.segments || [];
  const activeStep = state.segmentIndex;

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <SchoolIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">Lesson Progress</Typography>
        </Box>

        <Stepper activeStep={activeStep} orientation="vertical">
          {segments.map((segment, index) => (
            <Step key={index} completed={index < activeStep}>
              <StepLabel
                optional={
                  index === activeStep ? (
                    <Typography variant="caption" color="primary">
                      Current
                    </Typography>
                  ) : null
                }
              >
                {segment.title}
              </StepLabel>
              <StepContent>
                <Typography variant="body2" color="text.secondary">
                  {segment.check_question}
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <Chip label={segment.emotion} size="small" sx={{ mr: 0.5 }} />
                  <Chip label={segment.motion} size="small" variant="outlined" />
                </Box>
              </StepContent>
            </Step>
          ))}
          <Step>
            <StepLabel>Quiz</StepLabel>
          </Step>
          <Step>
            <StepLabel>Complete</StepLabel>
          </Step>
        </Stepper>
      </CardContent>
    </Card>
  );
}

function QuizScoreCard({ state }: { state: GraphState }) {
  const hasScore = state.score !== null;
  const scorePercent = state.scorePercent || 0;

  const getScoreColor = () => {
    if (!hasScore) return 'grey.400';
    if (scorePercent >= 80) return '#4caf50';
    if (scorePercent >= 60) return '#ff9800';
    return '#f44336';
  };

  const getScoreEmoji = () => {
    if (!hasScore) return null;
    if (scorePercent >= 80) return '🎉';
    if (scorePercent >= 60) return '👍';
    return '💪';
  };

  return (
    <Card
      sx={{
        height: '100%',
        background: hasScore
          ? `linear-gradient(135deg, ${getScoreColor()}22, ${getScoreColor()}44)`
          : undefined,
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <EmojiEventsIcon sx={{ mr: 1, color: getScoreColor() }} />
          <Typography variant="h6">Quiz Score</Typography>
        </Box>

        {hasScore ? (
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h2" sx={{ fontWeight: 'bold', color: getScoreColor() }}>
              {state.score}/{state.scoreMax}
            </Typography>
            <Typography variant="h4" sx={{ mt: 1 }}>
              {scorePercent}% {getScoreEmoji()}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              {scorePercent >= 80
                ? 'Excellent work!'
                : scorePercent >= 60
                ? 'Good job!'
                : 'Keep practicing!'}
            </Typography>
          </Box>
        ) : (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h4" color="text.secondary">
              --
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {state.inQuiz ? 'Quiz in progress...' : 'Complete the lesson to take the quiz'}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export default function StudentDashboard() {
  const [state, setState] = useState<GraphState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchActiveSession() {
      try {
        const activeSessions = await api.getActiveSessions();
        if (activeSessions.length > 0) {
          setState(activeSessions[0]);
        } else {
          // Try to get the most recent session
          const sessions = await api.getSessions();
          if (sessions.length > 0) {
            const sessionState = await api.getSessionState(sessions[0].id);
            setState(sessionState);
          }
        }
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch session');
      } finally {
        setLoading(false);
      }
    }

    fetchActiveSession();
    const interval = setInterval(fetchActiveSession, 2000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!state) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <SmartToyIcon sx={{ fontSize: 80, color: 'grey.400', mb: 2 }} />
        <Typography variant="h5" color="text.secondary">
          No active lesson
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          Start a teaching session to see the student dashboard
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header with Student Info and Lesson Title */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          mb: 4,
          p: 3,
          bgcolor: 'primary.main',
          color: 'white',
          borderRadius: 2,
        }}
      >
        <Avatar
          sx={{
            width: 80,
            height: 80,
            bgcolor: 'white',
            color: 'primary.main',
            mr: 3,
          }}
        >
          <PersonIcon sx={{ fontSize: 50 }} />
        </Avatar>

        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
            {state.studentId}
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.9 }}>
            Lesson: {state.lessonTitle}
          </Typography>
        </Box>

        <Box sx={{ textAlign: 'right' }}>
          <Chip
            label={state.isComplete ? 'Completed' : state.inQuiz ? 'Quiz Time' : 'Learning'}
            sx={{
              bgcolor: 'white',
              color: 'primary.main',
              fontWeight: 'bold',
              fontSize: '1rem',
              py: 2,
            }}
          />
        </Box>
      </Box>

      {/* Overall Progress Bar */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body1" fontWeight="medium">
              Overall Progress
            </Typography>
            <Typography variant="body1" fontWeight="bold" color="primary">
              {state.progressPercent}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={state.progressPercent}
            sx={{ height: 12, borderRadius: 2 }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Segment {state.segmentIndex} of {state.totalSegments}
            {state.inQuiz && ' - Quiz in progress'}
            {state.isComplete && ' - Lesson complete!'}
          </Typography>
        </CardContent>
      </Card>

      {/* Main Content Grid */}
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        {/* Left Column - Captions */}
        <Box sx={{ flex: '1 1 400px', minWidth: 300 }}>
          <CaptionDisplay transcript={state.transcript} />
        </Box>

        {/* Right Column - Progress & Score */}
        <Box sx={{ flex: '1 1 300px', minWidth: 280 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <QuizScoreCard state={state} />
            <LessonProgressStepper state={state} />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
