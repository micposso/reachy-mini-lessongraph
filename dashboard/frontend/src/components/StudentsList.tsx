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
  Collapse,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import { api } from '../api';
import type { Student, Session } from '../types';

interface StudentRowProps {
  student: Student;
}

function StudentRow({ student }: StudentRowProps) {
  const [open, setOpen] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);

  const handleExpand = async () => {
    if (!open && sessions.length === 0) {
      setLoading(true);
      try {
        const data = await api.getStudentSessions(student.studentId);
        setSessions(data);
      } catch (err) {
        console.error('Failed to fetch sessions:', err);
      } finally {
        setLoading(false);
      }
    }
    setOpen(!open);
  };

  const scorePercent =
    student.bestScore !== null && student.scoreMax
      ? Math.round((student.bestScore / student.scoreMax) * 100)
      : null;

  return (
    <>
      <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton size="small" onClick={handleExpand}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          <Typography variant="body1" fontWeight="medium">
            {student.studentId}
          </Typography>
        </TableCell>
        <TableCell align="center">{student.sessionCount}</TableCell>
        <TableCell align="center">
          {student.bestScore !== null ? (
            <Chip
              label={`${student.bestScore}/${student.scoreMax} (${scorePercent}%)`}
              color={
                scorePercent && scorePercent >= 80
                  ? 'success'
                  : scorePercent && scorePercent >= 60
                  ? 'warning'
                  : 'default'
              }
              size="small"
            />
          ) : (
            <Typography color="text.secondary">-</Typography>
          )}
        </TableCell>
        <TableCell align="right">
          {student.lastSession
            ? new Date(student.lastSession).toLocaleString()
            : '-'}
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={5}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Session History
              </Typography>
              {loading ? (
                <CircularProgress size={20} />
              ) : sessions.length === 0 ? (
                <Typography color="text.secondary">No sessions found</Typography>
              ) : (
                <List dense>
                  {sessions.map((session) => (
                    <ListItem key={session.id} divider>
                      <ListItemText
                        primary={session.lessonTitle || 'Unknown Lesson'}
                        secondary={`Started: ${new Date(session.startedAt).toLocaleString()} | Segment: ${session.segmentIndex}`}
                      />
                      {session.score !== null ? (
                        <Chip
                          label={`${session.score}/${session.scoreMax}`}
                          size="small"
                          color="primary"
                        />
                      ) : (
                        <Chip label="In Progress" size="small" color="info" />
                      )}
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export default function StudentsList() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStudents() {
      try {
        const data = await api.getStudents();
        setStudents(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch students');
      } finally {
        setLoading(false);
      }
    }

    fetchStudents();
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
        Students
      </Typography>

      {students.length === 0 ? (
        <Alert severity="info">
          No students found. Run a teaching session to create student records.
        </Alert>
      ) : (
        <Card>
          <CardContent>
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell width={50} />
                    <TableCell>Student ID</TableCell>
                    <TableCell align="center">Sessions</TableCell>
                    <TableCell align="center">Best Score</TableCell>
                    <TableCell align="right">Last Session</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {students.map((student) => (
                    <StudentRow key={student.studentId} student={student} />
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
