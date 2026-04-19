import { useState, useEffect } from 'react';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { StreamingTextDisplay } from './components/StreamingTextDisplay';
import { ModeQuickSelect } from './components/ModeQuickSelect';
import { VolumeWaveform } from './components/VolumeWaveform';
import { Button } from './components/ui/button';
import { Card, CardContent } from './components/ui/card';
import { useWhisperState } from './hooks/useWhisperState';
import { resizeWindowForTab } from './hooks/useWindowResize';
import './index.css';

type Tab = 'status' | 'modes' | 'config';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('status');
  const {
    config,
    status,
    isLoading,
    error,
    saveConfig,
    refreshStatus,
    startDaemon,
    stopDaemon,
    volumeLevel,
    isRecording,
  } = useWhisperState();

  useEffect(() => {
    resizeWindowForTab(activeTab);
  }, [activeTab]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">
            Loading Whisper Hotkey...
          </p>
        </div>
      </div>
    );
  }

  const getRecordingStatus = () => {
    if (isRecording) return 'Recording...';
    if (status.is_running) return 'Listening';
    return 'Stopped';
  };

  const getRecordingEmoji = () => {
    if (isRecording) return '🎙️';
    return '🔴';
  };

  return (
    <div className="flex h-screen w-screen flex-col bg-background">
      <div className="flex shrink-0 gap-0 border-b border-border">
        <button
          type="button"
          onClick={() => setActiveTab('status')}
          className={\`flex-1 px-2 py-3 text-xs font-medium transition-colors \${activeTab === 'status'
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-muted-foreground hover:text-foreground'
          }\`}
        >
          🎙️ Status
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('modes')}
          className={\`flex-1 px-2 py-3 text-xs font-medium transition-colors \${activeTab === 'modes'
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-muted-foreground hover:text-foreground'
          }\`}
        >
          ⚡ Modes
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('config')}
          className={\`flex-1 px-2 py-3 text-xs font-medium transition-colors \${activeTab === 'config'
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-muted-foreground hover:text-foreground'
          }\`}
        >
          ⚙️ Config
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'status' && (
          <div className="scroll-container tab-content flex flex-col p-4 space-y-4">
            {error && (
              <Card className="border-destructive bg-destructive/10">
                <CardContent className="p-3">
                  <p className="text-sm text-destructive-foreground">
                    {error}
                  </p>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-center">
                  <div className="inline-flex items-center rounded-full bg-muted px-3 py-1 text-xs font-medium text-foreground">
                    {config?.voice_activation_mode === 'toggle' ? '🔘 Toggle' : '✋ Hold'}
                  </div>
                </div>

                <div className="flex justify-center">
                  <VolumeWaveform volume={volumeLevel} isActive={status.is_running} />
                </div>

                <div className="flex items-center justify-center gap-2">
                  <span
                    className={`text-2xl ${isRecording ? 'animate-pulse' : ''}`}
                    role="img"
                    aria-label="Recording indicator"
                  >
                    {getRecordingEmoji()}
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {getRecordingStatus()}
                  </span>
                </div>

                <StreamingTextDisplay
                  text={status.stream_text}
                  isStreaming={status.is_running}
                />

                {status.pid && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      PID
                    </span>
                    <span className="text-xs font-mono text-foreground">
                      {status.pid}
                    </span>
                  </div>
                )}

                <div className="flex gap-2">
                  {!status.is_running ? (
                    <Button
                      onClick={startDaemon}
                      className="flex-1 text-xs"
                    >
                      Start
                    </Button>
                  ) : (
                    <Button
                      variant="destructive"
                      onClick={stopDaemon}
                      className="flex-1 text-xs"
                    >
                      Stop
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={refreshStatus}
                    className="text-xs"
                    title="Refresh daemon status"
                  >
                    ↻
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'modes' && config && (
          <div className="scroll-container tab-content flex flex-col p-4 space-y-4">
            <ModeQuickSelect
              currentMode={config.post_processing_mode}
              onModeChange={(mode) =>
                saveConfig({
                  ...config,
                  post_processing_mode: mode,
                  post_processing_enabled: mode !== 'off',
                })
              }
              disabled={status.is_running}
            />
            <div className="flex items-center justify-between rounded-md bg-muted px-3 py-2">
              <span className="text-xs text-muted-foreground">
                Current
              </span>
              <span className="text-xs font-semibold text-primary">
                {config.post_processing_enabled ? config.post_processing_mode : 'Off'}
              </span>
            </div>
            {status.is_running && (
              <div className="flex items-center gap-2 text-xs text-amber-400">
                <span>⚠️</span>
                <span>Stop daemon to apply changes</span>
              </div>
            )}
          </div>
        )}

        {activeTab === 'config' && config && (
          <div className="scroll-container tab-content flex flex-col p-4">
            <ConfigurationPanel
              config={config}
              onConfigChange={saveConfig}
              disabled={status.is_running}
            />
            {status.is_running && (
              <div className="mt-4 flex items-center gap-2 text-xs text-amber-400">
                <span>⚠️</span>
                <span>Stop daemon to apply changes</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="shrink-0 px-4 py-2">
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <kbd className="rounded border bg-muted px-1 py-0.5 font-mono text-[10px]">
              {config?.voice_activation_mode === 'toggle' ? 'Ctrl+Space' : 'Ctrl+Space'}
            </kbd>
            {config?.voice_activation_mode === 'toggle' ? 'Toggle' : 'Hold'}
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <kbd className="rounded border bg-muted px-1 py-0.5 font-mono text-[10px]">
              Ctrl+Shift+Alt+Space
            </kbd>
            Modes
          </span>
        </div>
      </div>
    </div>
  );
}

export default App;
