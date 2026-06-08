import { useState, useEffect, useRef, type KeyboardEvent } from 'react';
import type { Conversation } from './types';
import {
  fetchConversations,
  renameConversation,
  deleteConversation,
} from './api';
import { Plus, ChatCircle, PencilSimple, X } from '@phosphor-icons/react';

interface ConversationSidebarProps {
  workspaceId: string | undefined;
  activeConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewConversation: () => void;
  refreshTrigger?: number;
}

function groupConversations(
  conversations: Conversation[],
): { label: string; items: Conversation[] }[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'This Week', items: [] },
    { label: 'Older', items: [] },
  ];

  for (const conv of conversations) {
    const d = conv.updated_at ? new Date(conv.updated_at) : new Date(conv.created_at || 0);
    if (d >= today) {
      groups[0].items.push(conv);
    } else if (d >= yesterday) {
      groups[1].items.push(conv);
    } else if (d >= weekAgo) {
      groups[2].items.push(conv);
    } else {
      groups[3].items.push(conv);
    }
  }

  return groups.filter((g) => g.items.length > 0);
}

export default function ConversationSidebar({
  workspaceId,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  refreshTrigger,
}: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const renameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!workspaceId) {
      setConversations([]);
      return;
    }

    let cancelled = false;
    fetchConversations(workspaceId)
      .then((data) => {
        if (!cancelled) setConversations(data);
      })
      .catch((err) => console.error('Failed to load conversations:', err));

    return () => {
      cancelled = true;
    };
  }, [workspaceId, refreshTrigger]);

  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingId]);

  const handleRenameStart = (conv: Conversation) => {
    setRenamingId(conv.id);
    setRenameValue(conv.title);
  };

  const handleRenameSubmit = async () => {
    if (!renamingId || !renameValue.trim()) {
      setRenamingId(null);
      return;
    }

    try {
      const updated = await renameConversation(renamingId, renameValue.trim());
      setConversations((prev) =>
        prev.map((c) => (c.id === updated.id ? updated : c)),
      );
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
    setRenamingId(null);
  };

  const handleRenameKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRenameSubmit();
    } else if (e.key === 'Escape') {
      setRenamingId(null);
    }
  };

  const handleDelete = async (convId: string) => {
    try {
      await deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConversationId === convId) {
        onNewConversation();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const grouped = groupConversations(conversations);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-slate-800">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 hover:text-blue-300 transition-colors font-medium text-sm group"
        >
          <Plus className="group-hover:scale-110 transition-transform" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {conversations.length === 0 ? (
          <div className="text-center text-slate-500 text-sm mt-8 px-4 flex flex-col items-center">
            <ChatCircle size={24} className="mb-2 opacity-50" />
            No conversations yet.
          </div>
        ) : (
          grouped.map((group) => (
            <div key={group.label} className="space-y-1">
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 px-2">
                {group.label}
              </div>
              {group.items.map((conv) => (
                <div
                  key={conv.id}
                  className={`group relative flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors text-sm ${
                    conv.id === activeConversationId
                      ? 'bg-slate-800 text-slate-100'
                      : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                  }`}
                  onClick={() => {
                    if (renamingId !== conv.id) onSelectConversation(conv.id);
                  }}
                >
                  <ChatCircle weight={conv.id === activeConversationId ? 'fill' : 'regular'} className="flex-shrink-0" />
                  
                  {renamingId === conv.id ? (
                    <input
                      ref={renameInputRef}
                      className="flex-1 bg-slate-950 border border-blue-500 rounded px-2 py-0.5 text-slate-100 outline-none text-sm min-w-0"
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={handleRenameKeyDown}
                      onBlur={handleRenameSubmit}
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <span className="flex-1 truncate">{conv.title}</span>
                  )}

                  <div className={`flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ${renamingId === conv.id ? 'hidden' : ''}`}>
                    <button
                      className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                      onClick={(e) => { e.stopPropagation(); handleRenameStart(conv); }}
                    >
                      <PencilSimple />
                    </button>
                    <button
                      className="p-1 text-slate-500 hover:text-red-400 transition-colors"
                      onClick={(e) => { e.stopPropagation(); handleDelete(conv.id); }}
                    >
                      <X />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
