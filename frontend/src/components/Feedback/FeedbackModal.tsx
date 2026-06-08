import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useWorkspace } from '../../context/WorkspaceContext';
import { motion, AnimatePresence } from 'framer-motion';
import { ChatTeardropText, Star, X } from '@phosphor-icons/react';
import { API_BASE, getAuthHeaders } from '../../lib/api';

export default function FeedbackModal() {
  const { currentUser } = useAuth();
  const { activeWorkspace } = useWorkspace();
  const [isOpen, setIsOpen] = useState(false);
  const [rating, setRating] = useState<number>(5);
  const [category, setCategory] = useState<string>('UI/UX');
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    const payload = {
      user_id: currentUser?.id || null,
      workspace_id: activeWorkspace?.id || null,
      rating,
      category,
      comment,
    };

    try {
      const response = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to submit feedback');
      }

      setSubmitSuccess(true);
      setComment('');
      setRating(5);
      setCategory('UI/UX');

      // Reset success state and close modal after 2 seconds
      setTimeout(() => {
        setSubmitSuccess(false);
        setIsOpen(false);
      }, 2000);
    } catch (err: any) {
      setErrorMsg(err.message || 'An error occurred while submitting.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <div className="fixed bottom-6 right-6 z-50">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 px-4 py-3 rounded-full bg-slate-900/80 border border-slate-800 text-blue-400 hover:text-blue-300 hover:border-slate-700 backdrop-blur-xl shadow-2xl transition-all cursor-pointer group"
          id="btn-feedback-trigger"
        >
          <ChatTeardropText className="w-5 h-5 group-hover:rotate-12 transition-transform" weight="duotone" />
          <span className="text-sm font-semibold">Feedback</span>
        </motion.button>
      </div>

      {/* Modal Overlay */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm"
            />

            {/* Modal Body */}
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="relative w-full max-w-md bg-slate-900/70 border border-slate-800/80 backdrop-blur-2xl rounded-2xl p-6 shadow-2xl text-slate-100 overflow-hidden"
            >
              {/* Decorative radial gradient inside modal */}
              <div className="absolute -top-[30%] -right-[30%] w-[60%] h-[60%] rounded-full bg-blue-500/10 blur-[50px] pointer-events-none" />

              <div className="flex justify-between items-center mb-4 relative z-10">
                <h3 className="text-lg font-bold text-slate-50 flex items-center gap-2">
                  <span className="text-blue-500">✦</span> Send Feedback
                </h3>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 rounded-full text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {submitSuccess ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center py-8 text-center"
                >
                  <div className="w-12 h-12 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center mb-3">
                    <Star weight="fill" className="w-6 h-6 animate-pulse" />
                  </div>
                  <h4 className="text-lg font-bold text-slate-100 mb-1">Thank you!</h4>
                  <p className="text-sm text-slate-400">Your feedback has been submitted successfully.</p>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4 relative z-10">
                  {errorMsg && (
                    <div className="p-3 text-xs bg-red-950/50 border border-red-900/50 text-red-400 rounded-lg">
                      {errorMsg}
                    </div>
                  )}

                  {/* Rating Selector */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Rating
                    </label>
                    <div className="flex gap-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setRating(star)}
                          className="p-1 transition-transform hover:scale-110 cursor-pointer"
                        >
                          <Star
                            weight={star <= rating ? 'fill' : 'regular'}
                            className={`w-7 h-7 ${
                              star <= rating ? 'text-yellow-500 drop-shadow-[0_0_8px_rgba(234,179,8,0.3)]' : 'text-slate-600'
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Category Selector */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Category
                    </label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                    >
                      <option value="UI/UX">UI/UX Layout</option>
                      <option value="Bug">Bug Report</option>
                      <option value="Feature Request">Feature Request</option>
                      <option value="Accuracy">AI Answer Accuracy</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>

                  {/* Comments */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Your Comments
                    </label>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      required
                      placeholder="Tell us what you think or describe the issue..."
                      rows={4}
                      className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors resize-none"
                    />
                  </div>

                  {/* Context Info Display */}
                  <div className="pt-2 flex justify-between text-[11px] text-slate-500 border-t border-slate-800/60">
                    <span>User: {currentUser?.name || 'Guest'}</span>
                    <span>Workspace: {activeWorkspace?.name || 'Default'}</span>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsOpen(false)}
                      className="flex-1 py-2 rounded-lg bg-slate-800 border border-slate-700/50 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:text-slate-400 text-white text-sm font-medium transition-colors cursor-pointer flex justify-center items-center gap-2 shadow-[0_0_15px_rgba(59,130,246,0.3)]"
                    >
                      {isSubmitting ? (
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      ) : (
                        'Submit'
                      )}
                    </button>
                  </div>
                </form>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
