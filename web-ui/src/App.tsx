import { useState } from 'react';
import { useWhisperApi } from './hooks/useWhisperApi';
import { Mic, Settings, Activity } from 'lucide-react';

type Tab = 'status' | 'config' | 'diagnostics';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('status');
  const api = useWhisperApi();

  if (api.isLoading) {
    return <div className="p-8 text-center">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="max-w-6xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6 text-white">Whisper Hotkey Control</h1>

        {api.error && (
          <div className="mb-4 p-4 bg-red-900 border border-red-700 rounded-lg">
            <p className="text-red-200">{api.error}</p>
          </div>
        )}

        <div className="flex gap-2 mb-6 border-b border-gray-700 pb-4">
          <button
            onClick={() => setActiveTab('status')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
              activeTab === 'status'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            <Activity size={20} />
            <span>Status</span>
          </button>
          <button
            onClick={() => setActiveTab('config')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
              activeTab === 'config'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            <Settings size={20} />
            <span>Configuration</span>
          </button>
          <button
            onClick={() => setActiveTab('diagnostics')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
              activeTab === 'diagnostics'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            <Mic size={20} />
            <span>Diagnostics</span>
          </button>
        </div>

        <div className="bg-gray-800 rounded-xl p-6">
          {activeTab === 'status' && (
            <div>
              <div className="mb-4">
                <p className="text-lg mb-2">Daemon Status: <span className={`font-bold ${api.status.is_running ? 'text-green-400' : 'text-red-400'}`}>{api.status.is_running ? 'Running' : 'Stopped'}</span></p>
                {api.status.pid && <p className="text-sm text-gray-400">PID: {api.status.pid}</p>}
              </div>
              <div className="flex gap-4">
                {!api.status.is_running ? (
                  <button onClick={api.startDaemon} className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium">
                    Start Daemon
                  </button>
                ) : (
                  <button onClick={api.stopDaemon} className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium">
                    Stop Daemon
                  </button>
                )}
              </div>
              {api.status.stream_text && (
                <div className="mt-6 p-4 bg-gray-900 rounded-lg">
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Latest Transcription</h3>
                  <p className="text-gray-100">{api.status.stream_text}</p>
                </div>
              )}
            </div>
          )}
          {activeTab === 'config' && (
            <div>
              <h2 className="text-xl font-semibold mb-4 text-white">Configuration Panel</h2>
              <p className="text-gray-400">Configuration editor coming soon...</p>
            </div>
          )}
          {activeTab === 'diagnostics' && (
            <div>
              <h2 className="text-xl font-semibold mb-4 text-white">Diagnostics</h2>
              <p className="text-gray-400">System diagnostics coming soon...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
