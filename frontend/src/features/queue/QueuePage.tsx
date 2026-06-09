import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  PaperPlaneTilt, 
  Hourglass, 
  CheckCircle, 
  XCircle, 
  CaretDown, 
  CaretUp, 
  ArrowsClockwise, 
  ListBullets, 
  TerminalWindow,
  StopCircle
} from '@phosphor-icons/react';
import { useWorkspace } from '../../context/WorkspaceContext';
import { 
  submitWorkflow, 
  listWorkflows, 
  cancelWorkflow,
  streamWorkflowStatus,
  type WorkflowStatusResponse 
} from '../chat/api';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error';
}

export default function QueuePage() {
  const { activeWorkspace } = useWorkspace();
  const [input, setInput] = useState('');
  const [tasks, setTasks] = useState<WorkflowStatusResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({});
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const streamsRef = useRef<Record<string, () => void>>({});

  const addToast = (message: string, type: 'success' | 'error') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const setupStreamsForActiveTasks = (currentTasks: WorkflowStatusResponse[]) => {
    currentTasks.forEach((task) => {
      if ((task.status === 'QUEUED' || task.status === 'PROCESSING') && !streamsRef.current[task.workflow_id]) {
        const promise = streamWorkflowStatus(task.workflow_id, (update) => {
          setTasks((prev) => {
            const updated = prev.map((t) => {
              if (t.workflow_id === task.workflow_id) {
                // Check if status changed
                if (t.status !== update.status) {
                  if (update.status === 'COMPLETED') {
                    addToast(`Research Complete: "${t.question.slice(0, 40)}..."`, 'success');
                  } else if (update.status === 'FAILED') {
                    addToast(`Research Failed: "${t.question.slice(0, 40)}..."`, 'error');
                  }
                }
                return { ...t, ...update };
              }
              return t;
            });
            return updated;
          });
        });
        streamsRef.current[task.workflow_id] = () => {
          promise.then((abort) => abort && abort());
        };
      } else if ((task.status === 'COMPLETED' || task.status === 'FAILED') && streamsRef.current[task.workflow_id]) {
        streamsRef.current[task.workflow_id]();
        delete streamsRef.current[task.workflow_id];
      }
    });
  };

  const fetchTasksList = async (silent = false) => {
    if (!silent) setIsRefreshing(true);
    try {
      const data = await listWorkflows(activeWorkspace?.id);
      setTasks(data);
      setupStreamsForActiveTasks(data);
    } catch (err) {
      console.error('Failed to load tasks:', err);
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTasksList();
    return () => {
      Object.values(streamsRef.current).forEach((abort) => abort && abort());
      streamsRef.current = {};
    };
  }, [activeWorkspace?.id]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSubmitting) return;

    if (!activeWorkspace?.id) {
      addToast('Please select a workspace first.', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      await submitWorkflow(trimmed, activeWorkspace.id);
      addToast('Research task queued successfully', 'success');
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
      
      await fetchTasksList(true);
    } catch (err: any) {
      addToast(err.message || 'Failed to queue research task', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCancelTask = async (workflowId: string) => {
    try {
      await cancelWorkflow(workflowId);
      addToast('Workflow cancellation requested', 'success');
      setTasks(prev => prev.map(t => t.workflow_id === workflowId ? { ...t, status: 'FAILED', answer: 'Workflow cancelled by user.' } : t));
      if (streamsRef.current[workflowId]) {
        streamsRef.current[workflowId]();
        delete streamsRef.current[workflowId];
      }
    } catch (err: any) {
      addToast(err.message || 'Failed to cancel workflow', 'error');
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  const toggleExpandTask = (id: string) => {
    setExpandedTasks((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getStatusBadge = (status: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED') => {
    switch (status) {
      case 'QUEUED':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700/50">
            <Hourglass size={12} className="animate-pulse" />
            Queued
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <svg className="animate-spin h-3.5 w-3.5 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle size={14} weight="fill" />
            Completed
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <XCircle size={14} weight="fill" />
            Failed
          </span>
        );
    }
  };

  return (
    <div className="h-full flex flex-col md:flex-row min-w-0" id="queue-page">
      {/* ── Left Column: Task Creator & Info ── */}
      <div className="w-full md:w-[400px] shrink-0 border-b md:border-b-0 md:border-r border-slate-800/60 p-6 flex flex-col justify-between bg-slate-950/40 backdrop-blur-md">
        <div className="space-y-6">
          <div>
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4">
              <ListBullets size={20} className="text-indigo-400" />
            </div>
            <h2 className="text-lg font-bold text-slate-100">Research Queue</h2>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Submit complex research questions for background execution. The agent will run independently using retry policies and tool logging.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex flex-col gap-2 p-2 rounded-2xl bg-slate-900/40 border border-slate-800 focus-within:border-indigo-500/30 transition-colors">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Submit a background research query... (Enter to send)"
                rows={2}
                disabled={isSubmitting}
                className="w-full bg-transparent text-slate-100 text-sm placeholder:text-slate-600 resize-none focus:outline-none px-3 py-2 max-h-40"
              />
              <div className="flex justify-end p-1">
                <button
                  type="submit"
                  disabled={isSubmitting || !input.trim()}
                  className="flex items-center justify-center w-8 h-8 rounded-xl bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <PaperPlaneTilt size={16} weight="fill" />
                </button>
              </div>
            </div>
          </form>
        </div>

        <div className="hidden md:block pt-6 border-t border-slate-800/40 text-[10px] text-slate-600 space-y-2">
          <p>✓ Runs asynchronously via Temporal Workflows</p>
          <p>✓ Automatic workflow retries (max 2 retries)</p>
          <p>✓ Streams results and updates status automatically</p>
        </div>
      </div>

      {/* ── Right Column: Interactive Queue Logs ── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0 bg-slate-950/20">
        <header className="shrink-0 h-12 flex items-center justify-between px-6 border-b border-slate-800/40 bg-slate-950/60 backdrop-blur-sm">
          <h3 className="text-xs font-semibold text-slate-400 tracking-wider uppercase">
            Active Submissions ({tasks.length})
          </h3>
          <button 
            onClick={() => fetchTasksList(false)}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 disabled:opacity-50 transition-colors"
          >
            <ArrowsClockwise size={12} className={isRefreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </header>

        {/* Scrollable list */}
        <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
          {tasks.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-20 text-slate-600">
              <TerminalWindow size={40} weight="light" className="mb-4 opacity-50" />
              <p className="text-sm">No research tasks submitted yet.</p>
              <p className="text-xs text-slate-700 mt-1">Submit a question on the left to start background processing.</p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {tasks.map((task) => {
                const isExpanded = expandedTasks[task.workflow_id] || false;
                const isActive = task.status === 'QUEUED' || task.status === 'PROCESSING';
                return (
                  <motion.div
                    key={task.workflow_id}
                    layout
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -15 }}
                    className="p-5 rounded-2xl bg-slate-900/30 border border-slate-800/60 backdrop-blur-sm shadow-xl flex flex-col gap-4"
                  >
                    {/* Header bar */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <h4 className="text-sm font-semibold text-slate-100">{task.question}</h4>
                        <span className="text-[10px] text-slate-600 block">
                          ID: {task.workflow_id} · Created: {new Date(task.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        {isActive && (
                          <button
                            onClick={() => handleCancelTask(task.workflow_id)}
                            className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-slate-400 hover:text-red-400 bg-slate-800 hover:bg-red-500/10 border border-slate-700 hover:border-red-500/30 rounded-full transition-colors"
                            title="Cancel Workflow"
                          >
                            <StopCircle size={14} weight="fill" /> Cancel
                          </button>
                        )}
                        {getStatusBadge(task.status)}
                      </div>
                    </div>

                    {/* Completion status display */}
                    {task.status === 'COMPLETED' && task.answer && (
                      <div className="text-sm text-slate-300 leading-relaxed border-t border-slate-800/40 pt-4 prose prose-invert max-w-none">
                        <div className="font-semibold text-xs text-slate-400 mb-1">Answer</div>
                        <p>{task.answer}</p>
                      </div>
                    )}

                    {task.status === 'FAILED' && task.answer && (
                      <div className="text-sm text-red-400 border-t border-slate-800/40 pt-4 bg-red-950/10 p-3 rounded-lg border border-red-900/20">
                        <div className="font-semibold text-xs text-red-300 mb-1">Error / Cancelled</div>
                        <p>{task.answer}</p>
                      </div>
                    )}

                    {/* Tool trace logs */}
                    {task.tool_calls && task.tool_calls.length > 0 && (
                      <div className="border-t border-slate-800/40 pt-3">
                        <button
                          onClick={() => toggleExpandTask(task.workflow_id)}
                          className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                        >
                          {isExpanded ? <CaretUp size={14} /> : <CaretDown size={14} />}
                          {isExpanded ? 'Hide Trace' : `Show Tool Calls Trace (${task.tool_calls.length})`}
                        </button>

                        <AnimatePresence>
                          {isExpanded && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden space-y-2 mt-3 pl-2 border-l border-indigo-500/20"
                            >
                              {task.tool_calls.map((tc, index) => (
                                <div 
                                  key={index}
                                  className="text-xs bg-slate-900/50 border border-slate-800/80 rounded-xl p-3 space-y-1.5"
                                >
                                  <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                                    <span>STEP #{index + 1}</span>
                                    <span className="text-indigo-400 font-semibold">{tc.tool}</span>
                                  </div>
                                  <div className="space-y-1">
                                    <div className="text-[10px] text-slate-600 font-semibold uppercase">Input:</div>
                                    <pre className="font-mono text-[10px] bg-slate-950/60 p-2 rounded text-slate-400 overflow-x-auto whitespace-pre-wrap">
                                      {tc.input}
                                    </pre>
                                  </div>
                                  <div className="space-y-1">
                                    <div className="text-[10px] text-slate-600 font-semibold uppercase">Output:</div>
                                    <pre className="font-mono text-[10px] bg-slate-950/60 p-2 rounded text-emerald-400/90 overflow-x-auto whitespace-pre-wrap">
                                      {tc.output}
                                    </pre>
                                  </div>
                                </div>
                              ))}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
          )}
        </div>
      </div>

      {/* ── Fixed Animated Toast Notifications ── */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 30, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.85 }}
              transition={{ type: 'spring', damping: 25, stiffness: 350 }}
              className={`p-4 rounded-xl border shadow-2xl flex items-center gap-3 backdrop-blur-md pointer-events-auto ${
                toast.type === 'success'
                  ? 'bg-slate-900/90 border-emerald-500/30 text-emerald-300'
                  : 'bg-slate-900/90 border-red-500/30 text-red-300'
              }`}
            >
              {toast.type === 'success' ? (
                <CheckCircle size={18} weight="fill" className="text-emerald-400 shrink-0" />
              ) : (
                <XCircle size={18} weight="fill" className="text-red-400 shrink-0" />
              )}
              <span className="text-xs font-semibold text-slate-200">{toast.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
