import { createBrowserRouter } from 'react-router-dom';
import DashboardLayout from './components/Layout/DashboardLayout';
import ChatPage from './features/chat/ChatPage';
import AgentPage from './features/agent/AgentPage';
import UsagePage from './features/usage/UsagePage';
import QueuePage from './features/queue/QueuePage';
import LoginPage from './features/auth/LoginPage';
import RegisterPage from './features/auth/RegisterPage';
import ProtectedRoute from './features/auth/ProtectedRoute';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <DashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <ChatPage /> },
      { path: 'agent', element: <AgentPage /> },
      { path: 'queue', element: <QueuePage /> },
      { path: 'usage', element: <UsagePage /> },
    ],
  },
]);
