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
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const { currentUser, isAuthenticated } = useAuth();

  const refresh = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const [u, w] = await Promise.all([fetchUsers(), fetchWorkspaces()]);
      setUsers(u);
      setWorkspaces(w);

      if (!activeWorkspace && w.length > 0) setActiveWorkspace(w[0]);
    } catch (err) {
      console.error('Failed to load workspace data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]); // removed activeWorkspace to avoid infinite loop on mount

  useEffect(() => {
    if (currentUser) {
      setActiveUser(currentUser);
    } else {
      setActiveUser(null);
    }
  }, [currentUser]);

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
        setActiveWorkspace,
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
