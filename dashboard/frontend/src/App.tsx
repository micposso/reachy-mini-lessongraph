import { useState } from 'react';
import {
  Box,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Container,
  ThemeProvider,
  createTheme,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SchoolIcon from '@mui/icons-material/School';
import PeopleIcon from '@mui/icons-material/People';
import PlayCircleIcon from '@mui/icons-material/PlayCircle';
import MonitorIcon from '@mui/icons-material/Monitor';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import FaceIcon from '@mui/icons-material/Face';

import StudentDashboard from './components/StudentDashboard';
import DashboardOverview from './components/DashboardOverview';
import LessonsList from './components/LessonsList';
import StudentsList from './components/StudentsList';
import SessionsList from './components/SessionsList';
import ActiveSessions from './components/ActiveSessions';

const drawerWidth = 240;

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#9c27b0',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

type View = 'student' | 'dashboard' | 'lessons' | 'students' | 'sessions' | 'active';

const menuItems: { id: View; label: string; icon: React.ReactNode }[] = [
  { id: 'student', label: 'My Lesson', icon: <FaceIcon /> },
  { id: 'dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
  { id: 'active', label: 'Live Monitor', icon: <MonitorIcon /> },
  { id: 'lessons', label: 'Lessons', icon: <SchoolIcon /> },
  { id: 'students', label: 'Students', icon: <PeopleIcon /> },
  { id: 'sessions', label: 'Sessions', icon: <PlayCircleIcon /> },
];

function App() {
  const [currentView, setCurrentView] = useState<View>('student');

  const renderView = () => {
    switch (currentView) {
      case 'student':
        return <StudentDashboard />;
      case 'dashboard':
        return <DashboardOverview />;
      case 'lessons':
        return <LessonsList />;
      case 'students':
        return <StudentsList />;
      case 'sessions':
        return <SessionsList />;
      case 'active':
        return <ActiveSessions />;
      default:
        return <StudentDashboard />;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ display: 'flex' }}>
        <CssBaseline />

        <AppBar
          position="fixed"
          sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
        >
          <Toolbar>
            <SmartToyIcon sx={{ mr: 2 }} />
            <Typography variant="h6" noWrap component="div">
              Reachy Teacher Dashboard
            </Typography>
          </Toolbar>
        </AppBar>

        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
            },
          }}
        >
          <Toolbar />
          <Box sx={{ overflow: 'auto' }}>
            <List>
              {menuItems.map((item) => (
                <ListItem key={item.id} disablePadding>
                  <ListItemButton
                    selected={currentView === item.id}
                    onClick={() => setCurrentView(item.id)}
                  >
                    <ListItemIcon>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.label} />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Box>
        </Drawer>

        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            bgcolor: 'background.default',
            minHeight: '100vh',
          }}
        >
          <Toolbar />
          <Container maxWidth="xl">{renderView()}</Container>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
