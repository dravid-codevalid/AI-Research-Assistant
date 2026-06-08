import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { motion } from 'framer-motion';
import { ChatCircle, ChartLineUp, Robot, ListBullets } from '@phosphor-icons/react';
import WorkspaceSelector from '../../features/workspace/WorkspaceSelector';
import FeedbackModal from '../Feedback/FeedbackModal';

export default function DashboardLayout() {
  const { currentUser, logout } = useAuth();
  const location = useLocation();
  
  return (
    <div className="h-screen bg-slate-950 text-slate-50 flex flex-col overflow-hidden">
      {/* Ambient Radial Mesh Gradients */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[40%] -left-[20%] w-[80%] h-[80%] rounded-full bg-indigo-900/15 blur-[120px]" />
        <div className="absolute top-[60%] -right-[20%] w-[60%] h-[60%] rounded-full bg-blue-900/10 blur-[100px]" />
      </div>

      {/* Top Navigation - Fluid Island Nav */}
      <div className="relative z-20 py-3 flex justify-center shrink-0 border-b border-slate-800/50">
        <motion.nav 
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.32, 0.72, 0, 1] }}
          className="px-6 py-2.5 rounded-full bg-slate-900/50 border border-slate-800 backdrop-blur-xl shadow-2xl flex items-center gap-6 md:gap-8"
        >
          <div className="flex items-center gap-2 font-bold text-slate-100 tracking-tight shrink-0">
            <span className="text-blue-500">✦</span> Research AI
          </div>
          
          <div className="w-px h-5 bg-slate-800 shrink-0" />
          
            <div className="flex items-center gap-1 shrink-0">
            <Link 
              to="/" 
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                location.pathname === '/' 
                  ? 'bg-blue-500/10 text-blue-400' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <ChatCircle weight={location.pathname === '/' ? 'fill' : 'regular'} />
              Chat
            </Link>
            <Link 
              to="/agent" 
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                location.pathname === '/agent' 
                  ? 'bg-emerald-500/10 text-emerald-400' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Robot weight={location.pathname === '/agent' ? 'fill' : 'regular'} />
              Agent
            </Link>
            <Link 
              to="/queue" 
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                location.pathname === '/queue' 
                  ? 'bg-indigo-500/10 text-indigo-400' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <ListBullets weight={location.pathname === '/queue' ? 'fill' : 'regular'} />
              Queue
            </Link>
            <Link 
              to="/usage" 
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                location.pathname === '/usage' 
                  ? 'bg-blue-500/10 text-blue-400' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <ChartLineUp weight={location.pathname === '/usage' ? 'fill' : 'regular'} />
              Usage
            </Link>
            </div>

          <div className="w-px h-5 bg-slate-800 shrink-0" />

          <WorkspaceSelector />

          <div className="w-px h-5 bg-slate-800 shrink-0" />
          
          <div className="flex items-center gap-3 text-sm text-slate-400 shrink-0">
            <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-xs text-slate-300 font-medium">
              {currentUser?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <span className="hidden sm:inline">{currentUser?.name || 'User'}</span>
            <button onClick={logout} className="ml-2 sm:ml-4 hover:text-slate-100 transition-colors">Logout</button>
          </div>
        </motion.nav>
      </div>

      {/* Main Content Area - fills remaining height */}
      <main className="relative z-10 flex-1 min-h-0 overflow-hidden">
        <Outlet />
      </main>
      <FeedbackModal />
    </div>
  );
}

