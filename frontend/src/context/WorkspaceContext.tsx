import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import {
  fetchUsers,
  fetchWorkspaces,
  type UserInfo,
  type WorkspaceInfo,
} from '../features/workspace/api';

// ── Context shape ─────────────────────────────────────────────────────────

interface WorkspaceContextValue {
  users: UserInfo[];
  workspaces: WorkspaceInfo[];
  activeUser: UserInfo | null;
  activeWorkspace: WorkspaceInfo | null;
  setActiveUser: (user: UserInfo | null) => void;
  setActiveWorkspace: (ws: WorkspaceInfo | null) => void;
  refresh: () => Promise<void>;
  isLoading: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [activeUser, setActiveUser] = useState<UserInfo | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceInfo | null>(() => {
    const saved = localStorage.getItem('activeWorkspace');
    if (!saved) return null;
    try {
      return JSON.parse(saved);
    } catch (e) {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);

  const { currentUser, isAuthenticated } = useAuth();

  const changeActiveWorkspace = useCallback((ws: WorkspaceInfo | null) => {
    setActiveWorkspace(ws);
    if (ws) {
      localStorage.setItem('activeWorkspace', JSON.stringify(ws));
    } else {
      localStorage.removeItem('activeWorkspace');
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const [u, w] = await Promise.all([fetchUsers(), fetchWorkspaces()]);
      setUsers(u);
      setWorkspaces(w);

      const savedWsStr = localStorage.getItem('activeWorkspace');
      let savedWs: WorkspaceInfo | null = null;
      if (savedWsStr) {
        try {
          const parsed = JSON.parse(savedWsStr);
          savedWs = w.find((x) => x.id === parsed.id) || null;
        } catch (e) {
          // ignore
        }
      }

      if (savedWs) {
        setActiveWorkspace(savedWs);
      } else if (w.length > 0) {
        setActiveWorkspace(w[0]);
        localStorage.setItem('activeWorkspace', JSON.stringify(w[0]));
      } else {
        setActiveWorkspace(null);
        localStorage.removeItem('activeWorkspace');
      }
    } catch (err) {
      console.error('Failed to load workspace data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (currentUser) {
      setActiveUser(currentUser);
    } else {
      setActiveUser(null);
    }
  }, [currentUser]);

  useEffect(() => {
    if (!isAuthenticated) {
      setActiveWorkspace(null);
      localStorage.removeItem('activeWorkspace');
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <WorkspaceContext.Provider
      value={{
        users,
        workspaces,
        activeUser,
        activeWorkspace,
        setActiveUser,
        setActiveWorkspace: changeActiveWorkspace,
        refresh,
        isLoading,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error('useWorkspace must be used within WorkspaceProvider');
  return ctx;
}
