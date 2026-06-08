import { useState } from 'react';
import { useWorkspace } from '../../context/WorkspaceContext';
import { createWorkspace } from './api';
import { CaretDown, Plus } from '@phosphor-icons/react';

export default function WorkspaceSelector() {
  const {
    workspaces,
    activeWorkspace,
    setActiveWorkspace,
    refresh,
    isLoading,
  } = useWorkspace();
  const [isCreating, setIsCreating] = useState(false);
  const [newWsName, setNewWsName] = useState('');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4 text-slate-500 text-sm">Loading…</div>
    );
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    try {
      const ws = await createWorkspace(newWsName.trim());
      await refresh();
      setActiveWorkspace(ws);
      setIsCreating(false);
      setNewWsName('');
    } catch (err) {
      console.error(err);
      alert('Failed to create workspace');
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">
        Workspace
      </div>

      <div className="relative">
        <select
          id="ws-select"
          className="w-full appearance-none bg-slate-950/60 border border-slate-800 text-slate-200 rounded-lg px-3 py-2 pr-8 outline-none transition-colors focus:border-blue-500/40 text-sm cursor-pointer"
          value={activeWorkspace?.id || ''}
          onChange={(e) => {
            const ws = workspaces.find((w) => w.id === e.target.value) || null;
            setActiveWorkspace(ws);
          }}
        >
          <option value="" disabled>Select workspace</option>
          {workspaces.map((ws) => (
            <option key={ws.id} value={ws.id}>
              {ws.name}
            </option>
          ))}
        </select>
        <CaretDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
      </div>

      {isCreating ? (
        <form onSubmit={handleCreate} className="flex flex-col gap-2">
          <input
            value={newWsName}
            onChange={(e) => setNewWsName(e.target.value)}
            placeholder="Workspace name"
            id="new-workspace"
            className="w-full bg-slate-950/60 border border-slate-800 text-slate-200 rounded-lg px-3 py-2 outline-none text-sm focus:border-blue-500/40 placeholder:text-slate-600"
            autoFocus
          />
          <div className="flex gap-2">
            <button type="submit" className="flex-1 px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-400 text-xs font-medium hover:bg-blue-500/25 transition-colors">Create</button>
            <button type="button" className="px-3 py-1.5 rounded-lg text-slate-500 text-xs font-medium hover:text-slate-300 transition-colors" onClick={() => setIsCreating(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <button
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-slate-700/60 text-slate-500 hover:text-slate-300 hover:border-slate-600 transition-colors text-xs font-medium"
          onClick={() => setIsCreating(true)}
        >
          <Plus size={12} weight="bold" />
          New Workspace
        </button>
      )}
    </div>
  );
}

