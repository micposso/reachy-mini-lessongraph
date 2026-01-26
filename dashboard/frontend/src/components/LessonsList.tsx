import { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TargetIcon from '@mui/icons-material/TrackChanges';
import TimerIcon from '@mui/icons-material/Timer';
import { api } from '../api';
import type { Lesson, PlanSegment } from '../types';

function SegmentCard({ segment, index }: { segment: PlanSegment; index: number }) {
  const emotionColors: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'info'> = {
    happy: 'success',
    excited: 'warning',
    encouraging: 'info',
    curious: 'primary',
    serious: 'default',
    neutral: 'default',
  };

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mr: 2 }}>
            {index + 1}. {segment.title}
          </Typography>
          <Chip
            label={segment.emotion}
            size="small"
            color={emotionColors[segment.emotion] || 'default'}
            sx={{ mr: 1 }}
          />
          <Chip label={segment.motion} size="small" variant="outlined" sx={{ mr: 1 }} />
          <Box sx={{ display: 'flex', alignItems: 'center', ml: 'auto' }}>
            <TimerIcon fontSize="small" sx={{ mr: 0.5, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.secondary">
              {Math.round(segment.duration_sec / 60)} min
            </Typography>
          </Box>
        </Box>

        <Typography variant="body2" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
          {segment.script.length > 300
            ? segment.script.substring(0, 300) + '...'
            : segment.script}
        </Typography>

        <Divider sx={{ my: 1 }} />

        <Typography variant="body2" color="primary">
          <strong>Check Question:</strong> {segment.check_question}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default function LessonsList() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchLessons() {
      try {
        const data = await api.getLessons();
        setLessons(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch lessons');
      } finally {
        setLoading(false);
      }
    }

    fetchLessons();
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
        Lessons
      </Typography>

      {lessons.length === 0 ? (
        <Alert severity="info">
          No lessons found. Run the planner to create a lesson.
        </Alert>
      ) : (
        lessons.map((lesson) => (
          <Accordion key={lesson.id} defaultExpanded={lessons.length === 1}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  {lesson.plan.title}
                </Typography>
                <Chip
                  label={`${lesson.plan.segments.length} segments`}
                  size="small"
                  sx={{ mr: 2 }}
                />
                <Typography variant="body2" color="text.secondary">
                  {new Date(lesson.createdAt).toLocaleDateString()}
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <TargetIcon sx={{ mr: 1 }} /> Learning Objectives
                </Typography>
                <List dense>
                  {lesson.plan.objectives.map((obj, i) => (
                    <ListItem key={i}>
                      <ListItemText primary={`${i + 1}. ${obj}`} />
                    </ListItem>
                  ))}
                </List>
              </Box>

              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                Lesson Segments
              </Typography>

              {lesson.plan.segments.map((segment, i) => (
                <SegmentCard key={i} segment={segment} index={i} />
              ))}

              {lesson.plan.next_lesson_hint && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <strong>Next Lesson Suggestion:</strong> {lesson.plan.next_lesson_hint}
                </Alert>
              )}
            </AccordionDetails>
          </Accordion>
        ))
      )}
    </Box>
  );
}
