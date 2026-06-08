import { useState, useEffect, useCallback } from 'react';
import { useChat } from './hooks/useChat';
import { fetchModels, type ModelInfo } from './api';
import { useWorkspace } from '../../context/WorkspaceContext';
import ConversationSidebar from './ConversationSidebar';
import ConversationHistory from './ConversationHistory';
import ChatInput from './ChatInput';

import { Trash } from '@phosphor-icons/react';

export default function ChatPage() {
  const {
    messages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    clearChat,
    loadConversation,
    startNewConversation,
  } = useChat();
  const { activeUser, activeWorkspace } = useWorkspace();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [sidebarRefresh, setSidebarRefresh] = useState(0);

  useEffect(() => {
    fetchModels()
      .then((data) => {
        setModels(data);
        if (data.length > 0 && !selectedModelId) {
          setSelectedModelId(data[0].id);
        }
      })
      .catch((err) => console.error('Failed to load models:', err));
  }, []);

  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      setSidebarRefresh((prev) => prev + 1);
    }
  }, [isLoading, messages.length]);

  const handleSend = (message: string, modelId?: string) => {
    sendMessage(message, modelId, activeUser?.id, activeWorkspace?.id);
  };

  const handleSelectConversation = useCallback(
    (convId: string) => {
      if (convId !== conversationId) {
        loadConversation(convId);
      }
    },
    [conversationId, loadConversation],
  );

  const handleNewConversation = useCallback(() => {
    startNewConversation();
  }, [startNewConversation]);

  return (
    <div className="flex h-full w-full">
      {/* ── Static Sidebar ── */}
      <aside className="w-60 shrink-0 hidden md:flex md:flex-col border-r border-slate-800/60 bg-slate-950/80">
        <div className="flex-1 min-h-0 overflow-y-auto">
          <ConversationSidebar
            workspaceId={activeWorkspace?.id}
            activeConversationId={conversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
            refreshTrigger={sidebarRefresh}
          />
        </div>
      </aside>

      {/* ── Main Chat Area ── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        {/* Static header */}
        <header className="shrink-0 h-12 flex items-center justify-between px-6 border-b border-slate-800/40 bg-slate-950/60 backdrop-blur-sm">
          <h2 className="text-sm font-medium text-slate-300 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            Research Assistant
          </h2>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-400 transition-colors"
            >
              <Trash size={14} />
              Clear
            </button>
          )}
        </header>

        {/* Scrollable chat history — this is the ONLY scrollable region */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          <ConversationHistory
            messages={messages}
            isLoading={isLoading}
            error={error}
          />
        </div>

        {/* Static input bar pinned to bottom */}
        <div className="shrink-0 border-t border-slate-800/40 bg-slate-950/80 backdrop-blur-sm px-6 py-4">
          <ChatInput
            onSend={handleSend}
            disabled={isLoading}
            models={models}
            selectedModelId={selectedModelId}
            onModelChange={setSelectedModelId}
          />
        </div>
      </div>
    </div>
  );
}

