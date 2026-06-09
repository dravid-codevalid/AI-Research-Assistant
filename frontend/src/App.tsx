import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { WorkspaceProvider } from './context/WorkspaceContext';
import { AuthProvider } from './context/AuthContext';
import { AgentProvider } from './context/AgentContext';
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error }: { error: any }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div className="p-8 rounded-3xl bg-red-500/10 border border-red-500/20 max-w-xl text-center">
        <h2 className="text-2xl font-bold text-red-400 mb-4">Something went wrong</h2>
        <p className="text-slate-300 font-mono text-sm bg-slate-950/50 p-4 rounded-xl text-left overflow-auto">
          {error.message}
        </p>
        <button 
          onClick={() => window.location.href = '/'}
          className="mt-6 px-6 py-2 bg-red-500 hover:bg-red-400 text-slate-950 font-semibold rounded-xl transition-colors"
        >
          Return Home
        </button>
      </div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <AuthProvider>
        <WorkspaceProvider>
          <AgentProvider>
            <RouterProvider router={router} />
          </AgentProvider>
        </WorkspaceProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
