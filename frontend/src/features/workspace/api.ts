import { API_BASE, getAuthHeaders } from '../../lib/api';

// ── Types ─────────────────────────────────────────────────────────────────

export interface UserInfo {
  id: string;
  name: string;
  email: string;
  created_at?: string;
  is_admin?: boolean;
}

export interface WorkspaceInfo {
  id: string;
  name: string;
  created_at?: string;
  litellm_team_id?: string;
}

export interface MemberInfo {
  user_id: string;
  user_name: string;
  user_email: string;
  role: string;
  litellm_key_alias?: string;
}

export interface UsageRecord {
  request_id?: string;
  user_id?: string;
  user_name?: string;
  team_id?: string;
  workspace_name?: string;
  model?: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  spend: number;
  created_at?: string;
  source?: string;
}

export interface PageBreakdown {
  page: string;
  total_tokens: number;
  total_spend: number;
  request_count: number;
}

export interface UsageData {
  records: UsageRecord[];
  total_spend: number;
  total_tokens: number;
  page_breakdown?: PageBreakdown[];
}

// ── Users ─────────────────────────────────────────────────────────────────

export async function fetchUsers(): Promise<UserInfo[]> {
  const res = await fetch(`${API_BASE}/users`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Failed to fetch users');
  return res.json();
}

export async function fetchMe(): Promise<UserInfo> {
  const res = await fetch(`${API_BASE}/users/me`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Failed to fetch current user');
  return res.json();
}

export async function createUser(name: string, email: string): Promise<UserInfo> {
  const res = await fetch(`${API_BASE}/users`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ name, email }),
  });
  if (!res.ok) throw new Error('Failed to create user');
  return res.json();
}

// ── Workspaces ────────────────────────────────────────────────────────────

export async function fetchWorkspaces(): Promise<WorkspaceInfo[]> {
  const res = await fetch(`${API_BASE}/workspaces`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Failed to fetch workspaces');
  return res.json();
}

export async function createWorkspace(
  name: string,
  allowedModels: string[] = [],
): Promise<WorkspaceInfo> {
  const res = await fetch(`${API_BASE}/workspaces`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ name, allowed_models: allowedModels }),
  });
  if (!res.ok) throw new Error('Failed to create workspace');
  return res.json();
}

export async function fetchMembers(workspaceId: string): Promise<MemberInfo[]> {
  const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/members`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Failed to fetch members');
  return res.json();
}

export async function addMember(
  workspaceId: string,
  userId: string,
  role: string = 'member',
): Promise<MemberInfo> {
  const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/members`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ user_id: userId, role }),
  });
  if (!res.ok) throw new Error('Failed to add member');
  return res.json();
}

// ── Usage ─────────────────────────────────────────────────────────────────

export async function fetchUsage(
  userId?: string,
  teamId?: string,
): Promise<UsageData> {
  const params = new URLSearchParams();
  if (userId) params.set('user_id', userId);
  if (teamId) params.set('team_id', teamId);

  const res = await fetch(`${API_BASE}/usage?${params.toString()}`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Failed to fetch usage data');
  return res.json();
}
