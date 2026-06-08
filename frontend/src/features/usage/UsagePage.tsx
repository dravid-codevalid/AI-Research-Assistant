import { useState, useEffect, useCallback } from 'react';
import { fetchUsage, type UsageData } from '../workspace/api';
import { useWorkspace } from '../../context/WorkspaceContext';
import { useAuth } from '../../context/AuthContext';
import Button from '../../components/Button/Button';
import { ArrowsClockwise, Coins, CurrencyDollar, ChartLineUp, Database, Lightning, ChatCircle, Robot, ListBullets } from '@phosphor-icons/react';

export default function UsagePage() {
  const { workspaces, users, activeWorkspace } = useWorkspace();
  const { currentUser } = useAuth();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterUser, setFilterUser] = useState<string>('');
  const [filterWorkspace, setFilterWorkspace] = useState<string>('');

  const loadUsage = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchUsage(
        filterUser || undefined,
        filterWorkspace || undefined,
      );
      setUsage(data);
    } catch {
      setError('Failed to load usage data.');
    } finally {
      setIsLoading(false);
    }
  }, [filterUser, filterWorkspace]);

  useEffect(() => {
    loadUsage();
  }, [loadUsage]);

  // Auto-populate workspace filter from active workspace
  useEffect(() => {
    if (activeWorkspace && !filterWorkspace) {
      setFilterWorkspace(activeWorkspace.litellm_team_id || activeWorkspace.id);
    }
  }, [activeWorkspace]);

  return (
    <div className="h-full w-full flex flex-col p-8 gap-8 overflow-y-auto">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-medium text-slate-100 tracking-tight flex items-center gap-3">
            <span className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400">
              <ChartLineUp size={20} />
            </span>
            Token Usage Dashboard
          </h2>
          <p className="text-sm text-slate-400 mt-2">
            Track consumption and spend across models and workspaces.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={loadUsage}
          disabled={isLoading}
          icon={<ArrowsClockwise className={isLoading ? 'animate-spin' : ''} />}
        >
          Refresh Data
        </Button>
      </header>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 flex items-center gap-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
          <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-400">
            <Coins weight="duotone" size={24} />
          </div>
          <div>
            <div className="text-3xl font-semibold text-slate-100 tracking-tight">
              {usage ? usage.total_tokens.toLocaleString() : '—'}
            </div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider mt-1">Total Tokens</div>
          </div>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 flex items-center gap-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <CurrencyDollar weight="duotone" size={24} />
          </div>
          <div>
            <div className="text-3xl font-semibold text-slate-100 tracking-tight">
              {usage ? `$${usage.total_spend.toFixed(6)}` : '—'}
            </div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider mt-1">Total Spend</div>
          </div>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 flex items-center gap-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
          <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400">
            <Database weight="duotone" size={24} />
          </div>
          <div>
            <div className="text-3xl font-semibold text-slate-100 tracking-tight">
              {usage ? usage.records.length.toLocaleString() : '—'}
            </div>
            <div className="text-sm text-slate-500 font-medium uppercase tracking-wider mt-1">Total Requests</div>
          </div>
        </div>
      </div>

      {/* Feature Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {(() => {
          const chatData = usage?.page_breakdown?.find(p => p.page === 'chat');
          const agentData = usage?.page_breakdown?.find(p => p.page === 'agent');
          const queueData = usage?.page_breakdown?.find(p => p.page === 'queue');
          return (
            <>
              <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 flex items-center gap-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400">
                  <ChatCircle weight="duotone" size={24} />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-100 mb-1">Chat</div>
                  <div className="text-lg font-semibold text-slate-200 tracking-tight">
                    {chatData ? chatData.total_tokens.toLocaleString() : '—'} <span className="text-xs text-slate-500 font-medium">tokens</span>
                  </div>
                  <div className="text-xs text-blue-400 font-mono">
                    {chatData ? `$${chatData.total_spend.toFixed(6)}` : '—'}
                  </div>
                </div>
              </div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 flex items-center gap-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <div className="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                  <Robot weight="duotone" size={24} />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-100 mb-1">Agent</div>
                  <div className="text-lg font-semibold text-slate-200 tracking-tight">
                    {agentData ? agentData.total_tokens.toLocaleString() : '—'} <span className="text-xs text-slate-500 font-medium">tokens</span>
                  </div>
                  <div className="text-xs text-emerald-400 font-mono">
                    {agentData ? `$${agentData.total_spend.toFixed(6)}` : '—'}
                  </div>
                </div>
              </div>
              <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 flex items-center gap-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                  <ListBullets weight="duotone" size={24} />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-100 mb-1">Queue</div>
                  <div className="text-lg font-semibold text-slate-200 tracking-tight">
                    {queueData ? queueData.total_tokens.toLocaleString() : '—'} <span className="text-xs text-slate-500 font-medium">tokens</span>
                  </div>
                  <div className="text-xs text-indigo-400 font-mono">
                    {queueData ? `$${queueData.total_spend.toFixed(6)}` : '—'}
                  </div>
                </div>
              </div>
            </>
          );
        })()}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 bg-slate-900/30 p-4 rounded-2xl border border-slate-800/50">
        <div className="flex-1 min-w-[200px] relative group">
          <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 ml-1">Workspace Filter</label>
          <select
            className="w-full appearance-none bg-slate-950/50 border border-slate-800 text-slate-100 rounded-xl px-4 py-2.5 outline-none transition-colors focus:border-blue-500/50 focus:bg-slate-900 text-sm cursor-pointer shadow-inner"
            value={filterWorkspace}
            onChange={(e) => setFilterWorkspace(e.target.value)}
          >
            <option value="">All Workspaces</option>
            {workspaces.map((ws) => (
              <option key={ws.id} value={ws.litellm_team_id || ws.id}>
                {ws.name}
              </option>
            ))}
          </select>
        </div>
        {currentUser?.is_admin && (
          <div className="flex-1 min-w-[200px] relative group">
            <label className="block text-xs font-medium text-slate-500 uppercase tracking-wider mb-2 ml-1">User Filter</label>
            <select
              className="w-full appearance-none bg-slate-950/50 border border-slate-800 text-slate-100 rounded-xl px-4 py-2.5 outline-none transition-colors focus:border-blue-500/50 focus:bg-slate-900 text-sm cursor-pointer shadow-inner"
              value={filterUser}
              onChange={(e) => setFilterUser(e.target.value)}
            >
              <option value="">All Users</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-hidden flex flex-col min-h-0 bg-slate-900/50 border border-slate-800 rounded-3xl relative shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
        {error && (
          <div className="absolute inset-x-0 top-0 p-3 bg-red-500/10 border-b border-red-500/20 text-red-400 text-sm text-center z-10">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-4">
            <ArrowsClockwise className="animate-spin text-blue-500" size={32} />
            <span className="text-sm font-medium tracking-wide">Crunching usage data...</span>
          </div>
        ) : usage && usage.records.length > 0 ? (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-left border-collapse text-sm whitespace-nowrap">
              <thead className="sticky top-0 bg-slate-950/90 backdrop-blur-xl z-10">
                <tr className="text-slate-400 border-b border-slate-800">
                  <th className="px-6 py-4 font-medium">Source</th>
                  <th className="px-6 py-4 font-medium">Workspace</th>
                  <th className="px-6 py-4 font-medium">User</th>
                  <th className="px-6 py-4 font-medium">Model</th>
                  <th className="px-6 py-4 font-medium text-right">Tokens</th>
                  <th className="px-6 py-4 font-medium text-right">Spend</th>
                  <th className="px-6 py-4 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {usage.records.map((rec, idx) => (
                  <tr key={rec.request_id || idx} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                        rec.source === 'litellm' 
                          ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' 
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                        {rec.source === 'litellm' ? <Lightning weight="bold" /> : <Database weight="bold" />}
                        {rec.source === 'litellm' ? 'LiteLLM' : 'DB'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-300 text-xs">
                      {rec.workspace_name || rec.team_id || '—'}
                    </td>
                    <td className="px-6 py-4 text-slate-300 text-xs">
                      {rec.user_name || rec.user_id || '—'}
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono text-xs px-2.5 py-1 rounded bg-slate-950 text-slate-300 border border-slate-800">
                        {rec.model || 'unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right text-slate-300 font-mono text-xs">
                      <span className="text-slate-500 mr-2" title={`Prompt: ${rec.prompt_tokens} / Completion: ${rec.completion_tokens}`}>
                        {rec.prompt_tokens} + {rec.completion_tokens} =
                      </span>
                      <span className="font-semibold text-slate-200">{rec.total_tokens.toLocaleString()}</span>
                    </td>
                    <td className="px-6 py-4 text-right text-emerald-400 font-mono text-xs font-semibold">
                      ${rec.spend.toFixed(6)}
                    </td>
                    <td className="px-6 py-4 text-slate-500 text-xs">
                      {rec.created_at ? new Date(rec.created_at).toLocaleString([], {
                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                      }) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-4 px-6 text-center">
            <div className="w-16 h-16 rounded-full bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-600 mb-2 shadow-inner">
              <Database size={32} weight="duotone" />
            </div>
            <p className="text-slate-300 font-medium text-lg">No usage data found</p>
            <p className="text-sm max-w-sm">There are no records matching your current filters. Start asking questions in the chat to generate token usage.</p>
          </div>
        )}
      </div>
    </div>
  );
}
