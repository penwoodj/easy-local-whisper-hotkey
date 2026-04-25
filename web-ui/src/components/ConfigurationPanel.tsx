import { useState, useEffect } from 'react';
import { Save, RotateCcw, AlertCircle, Check, FileText, Settings2, AudioLines, Sparkles, Bolt, Activity } from 'lucide-react';
import { useWhisperApi } from '../hooks/useWhisperApi';
import type { WhisperConfig } from '../api/types';
import { TextInput } from './TextInput';
import { NumericInput } from './NumericInput';
import { ToggleSwitch } from './ToggleSwitch';
import { SelectInput } from './SelectInput';
import { FilePickerInput } from './FilePickerInput';

const POST_PROCESSING_MODES: readonly { value: WhisperConfig['WHISPER_POST_PROCESSING_MODE']; label: string }[] = [
  { value: 'off', label: 'Off' },
  { value: 'light', label: 'Light' },
  { value: 'aggressive', label: 'Aggressive' },
  { value: 'agentic', label: 'Agentic' },
  { value: 'writing', label: 'Writing' },
  { value: 'code', label: 'Code' },
  { value: 'structure', label: 'Structure' },
  { value: 'persona', label: 'Persona' },
  { value: 'clarity', label: 'Clarity' },
] as const;

const POST_PROCESSING_TRIGGERS: readonly { value: WhisperConfig['WHISPER_POST_PROCESSING_TRIGGER']; label: string }[] = [
  { value: 'always', label: 'Always' },
  { value: 'manual', label: 'Manual' },
  { value: 'auto_long', label: 'Auto (Long Text)' },
  { value: 'preview', label: 'Preview' },
] as const;

const ACTIVATION_MODES: readonly { value: WhisperConfig['WHISPER_ACTIVATION_MODE']; label: string }[] = [
  { value: 'hold', label: 'Hold to Speak' },
  { value: 'toggle', label: 'Toggle On/Off' },
] as const;

const LANGUAGES = [
  'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh',
  'ar', 'hi', 'tr', 'vi', 'th', 'nl', 'pl', 'sv', 'da', 'fi',
  'no', 'he', 'uk', 'el', 'cs', 'ro', 'hu', 'id', 'ms', 'bn',
  'ta', 'te', 'mr', 'ur', 'fa', 'ca', 'sw', 'af', 'sq', 'am',
  'hy', 'az', 'be', 'bg', 'my', 'eu', 'gl', 'ka', 'gu', 'is',
  'jv', 'kn', 'kk', 'km', 'lo', 'la', 'lv', 'mk', 'ml', 'mn',
  'ne', 'pa', 'si', 'sl', 'sd', 'su', 'tg', 'uz', 'yi', 'zu',
].map((lang) => ({ value: lang, label: lang.toUpperCase() }));

interface SectionProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}

function Section({ title, description, icon, children }: SectionProps) {
  return (
    <div className="bg-gray-750/50 rounded-xl p-6 border border-gray-700/50 backdrop-blur-sm transition-all hover:border-gray-600/50 hover:shadow-xl hover:shadow-black/20">
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-gray-700/50">
        <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
          {icon}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white tracking-tight">{title}</h3>
          <p className="text-sm text-gray-400">{description}</p>
        </div>
      </div>
      <div className="space-y-4">
        {children}
      </div>
    </div>
  );
}

interface ConfigPanelProps {
  config: WhisperConfig;
  onChange: (config: WhisperConfig) => void;
  onSave: () => Promise<void>;
  onReset: () => Promise<void>;
  isSaving: boolean;
  isResetting: boolean;
  error: string | null;
}

function ConfigPanel({ config, onChange, onSave, onReset, isSaving, isResetting, error }: ConfigPanelProps) {
  const [localConfig, setLocalConfig] = useState<WhisperConfig>(config);
  const [showToast, setShowToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    setLocalConfig(config);
  }, [config]);

  const handleFieldChange = <K extends keyof WhisperConfig>(field: K, value: WhisperConfig[K]) => {
    setLocalConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    try {
      onChange(localConfig);
      await onSave();
      setShowToast({ type: 'success', message: 'Configuration saved successfully!' });
      setTimeout(() => setShowToast(null), 3000);
    } catch (err) {
      setShowToast({ type: 'error', message: 'Failed to save configuration. Please try again.' });
      setTimeout(() => setShowToast(null), 5000);
    }
  };

  const handleReset = async () => {
    try {
      await onReset();
      setShowToast({ type: 'success', message: 'Configuration reset to defaults!' });
      setTimeout(() => setShowToast(null), 3000);
    } catch (err) {
      setShowToast({ type: 'error', message: 'Failed to reset configuration. Please try again.' });
      setTimeout(() => setShowToast(null), 5000);
    }
  };

  const hasChanges = JSON.stringify(localConfig) !== JSON.stringify(config);

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between mb-6 sticky top-0 z-10 bg-gray-800/95 backdrop-blur-sm p-4 rounded-xl border border-gray-700/50">
        <div className="flex items-center gap-3">
          <Settings2 size={20} className="text-blue-400" />
          <span className="text-sm text-gray-300">
            {hasChanges ? (
              <span className="text-yellow-400 font-medium">Unsaved changes</span>
            ) : (
              <span className="text-green-400 font-medium">All changes saved</span>
            )}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleReset}
            disabled={isResetting || isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm border border-gray-600 hover:border-gray-500"
          >
            <RotateCcw size={16} />
            <span>Reset to Defaults</span>
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!hasChanges || isSaving || isResetting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm border border-blue-500 hover:border-blue-400 shadow-lg shadow-blue-900/20"
          >
            {isSaving ? (
              <>
                <span className="animate-spin">⟳</span>
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save size={16} />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-900/20 border border-red-700 rounded-xl">
          <AlertCircle size={20} className="text-red-400 flex-shrink-0" />
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      {/* Toast Notification */}
      {showToast && (
        <div className={`fixed bottom-6 right-6 flex items-center gap-3 px-6 py-4 rounded-xl shadow-2xl backdrop-blur-sm border transition-all animate-in slide-in-from-bottom-2 duration-300 ${
          showToast.type === 'success'
            ? 'bg-green-900/90 border-green-600 text-green-100'
            : 'bg-red-900/90 border-red-600 text-red-100'
        }`}>
          {showToast.type === 'success' ? <Check size={20} /> : <AlertCircle size={20} />}
          <span className="font-medium">{showToast.message}</span>
        </div>
      )}

      {/* Paths Section */}
      <Section
        title="Paths & Binaries"
        description="Configure paths to Whisper CLI and model files"
        icon={<FileText size={20} />}
      >
        <FilePickerInput
          label="Whisper CLI Path"
          name="WHISPER_CLI"
          value={localConfig.WHISPER_CLI}
          onChange={(value) => handleFieldChange('WHISPER_CLI', value)}
          placeholder="/usr/local/bin/whisper-cli"
          required
          error={!localConfig.WHISPER_CLI ? 'Whisper CLI path is required' : ''}
        />
        <FilePickerInput
          label="Model File Path"
          name="WHISPER_MODEL"
          value={localConfig.WHISPER_MODEL}
          onChange={(value) => handleFieldChange('WHISPER_MODEL', value)}
          placeholder="/path/to/model.gguf"
          required
          error={!localConfig.WHISPER_MODEL ? 'Model path is required' : ''}
        />
        <FilePickerInput
          label="Log File Path"
          name="WHISPER_LOG_FILE"
          value={localConfig.WHISPER_LOG_FILE}
          onChange={(value) => handleFieldChange('WHISPER_LOG_FILE', value)}
          placeholder="/var/log/whisper-hotkey.log"
        />
      </Section>

      {/* Audio Section */}
      <Section
        title="Audio Configuration"
        description="Audio input source and preferences"
        icon={<AudioLines size={20} />}
      >
        <TextInput
          label="Audio Source"
          name="WHISPER_AUDIO_SOURCE"
          value={localConfig.WHISPER_AUDIO_SOURCE}
          onChange={(value) => handleFieldChange('WHISPER_AUDIO_SOURCE', value)}
          placeholder="alsa_input.pci-0000_00_1f.3.analog-stereo"
          required
        />
        <TextInput
          label="Preferred Sources"
          name="WHISPER_PREFERRED_SOURCES"
          value={localConfig.WHISPER_PREFERRED_SOURCES}
          onChange={(value) => handleFieldChange('WHISPER_PREFERRED_SOURCES', value)}
          placeholder="alsa_input.*,pipewire.*"
          error={
            localConfig.WHISPER_PREFERRED_SOURCES &&
            !localConfig.WHISPER_PREFERRED_SOURCES.match(/^[a-z0-9_*,.\s-]+$/i)
              ? 'Invalid source pattern'
              : ''
          }
        />
      </Section>

      {/* Text Processing Section */}
      <Section
        title="Text Processing"
        description="Language and transcription processing options"
        icon={<Sparkles size={20} />}
      >
        <SelectInput
          label="Language"
          name="WHISPER_LANGUAGE"
          value={localConfig.WHISPER_LANGUAGE}
          onChange={(value) => handleFieldChange('WHISPER_LANGUAGE', value)}
          options={LANGUAGES}
        />
        <TextInput
          label="Suppress Regex"
          name="WHISPER_SUPPRESS_REGEX"
          value={localConfig.WHISPER_SUPPRESS_REGEX}
          onChange={(value) => handleFieldChange('WHISPER_SUPPRESS_REGEX', value)}
          placeholder="[um|uh|like|you know]"
          error={
            localConfig.WHISPER_SUPPRESS_REGEX &&
            !localConfig.WHISPER_SUPPRESS_REGEX.match(/^\[.*\]$/)
              ? 'Invalid regex pattern (use [pattern])'
              : ''
          }
        />
        <ToggleSwitch
          label="Suppress Non-Speech Transitions"
          name="WHISPER_SUPPRESS_NST"
          checked={localConfig.WHISPER_SUPPRESS_NST}
          onChange={(value) => handleFieldChange('WHISPER_SUPPRESS_NST', value)}
        />
        <ToggleSwitch
          label="Smart Punctuation"
          name="WHISPER_SMART_PUNCTUATION"
          checked={localConfig.WHISPER_SMART_PUNCTUATION}
          onChange={(value) => handleFieldChange('WHISPER_SMART_PUNCTUATION', value)}
        />
        <ToggleSwitch
          label="Words to Symbols"
          name="WHISPER_SYMBOL_WORDS_TO_SYMBOLS"
          checked={localConfig.WHISPER_SYMBOL_WORDS_TO_SYMBOLS}
          onChange={(value) => handleFieldChange('WHISPER_SYMBOL_WORDS_TO_SYMBOLS', value)}
        />
      </Section>

      {/* Streaming Section */}
      <Section
        title="Streaming Options"
        description="Real-time transcription and streaming behavior"
        icon={<Bolt size={20} />}
      >
        <NumericInput
          label="Chunk Duration"
          name="WHISPER_CHUNK_SECONDS"
          value={localConfig.WHISPER_CHUNK_SECONDS}
          onChange={(value) => handleFieldChange('WHISPER_CHUNK_SECONDS', value)}
          min={1}
          max={30}
          step={1}
          unit="s"
          error={
            localConfig.WHISPER_CHUNK_SECONDS < 1 || localConfig.WHISPER_CHUNK_SECONDS > 30
              ? 'Must be between 1 and 30 seconds'
              : ''
          }
        />
        <NumericInput
          label="Overlap Duration"
          name="WHISPER_OVERLAP_SECONDS"
          value={localConfig.WHISPER_OVERLAP_SECONDS}
          onChange={(value) => handleFieldChange('WHISPER_OVERLAP_SECONDS', value)}
          min={0}
          max={5}
          step={0.1}
          unit="s"
          error={
            localConfig.WHISPER_OVERLAP_SECONDS < 0 || localConfig.WHISPER_OVERLAP_SECONDS > 5
              ? 'Must be between 0 and 5 seconds'
              : ''
          }
        />
        <NumericInput
          label="Type Delay"
          name="WHISPER_TYPE_DELAY_MS"
          value={localConfig.WHISPER_TYPE_DELAY_MS}
          onChange={(value) => handleFieldChange('WHISPER_TYPE_DELAY_MS', value)}
          min={0}
          max={1000}
          step={10}
          unit="ms"
          error={
            localConfig.WHISPER_TYPE_DELAY_MS < 0 || localConfig.WHISPER_TYPE_DELAY_MS > 1000
              ? 'Must be between 0 and 1000ms'
              : ''
          }
        />
        <ToggleSwitch
          label="Direct Streaming"
          name="WHISPER_DIRECT_STREAMING"
          checked={localConfig.WHISPER_DIRECT_STREAMING}
          onChange={(value) => handleFieldChange('WHISPER_DIRECT_STREAMING', value)}
        />
      </Section>

      {/* Activation Section */}
      <Section
        title="Activation & Feedback"
        description="Voice activation mode and visual feedback"
        icon={<Activity size={20} />}
      >
        <SelectInput
          label="Activation Mode"
          name="WHISPER_ACTIVATION_MODE"
          value={localConfig.WHISPER_ACTIVATION_MODE}
          onChange={(value) => handleFieldChange('WHISPER_ACTIVATION_MODE', value)}
          options={ACTIVATION_MODES}
        />
        <ToggleSwitch
          label="Show Indicator"
          name="WHISPER_INDICATOR"
          checked={localConfig.WHISPER_INDICATOR}
          onChange={(value) => handleFieldChange('WHISPER_INDICATOR', value)}
        />
      </Section>

      {/* Post-Processing Section */}
      <Section
        title="Post-Processing"
        description="AI-powered text enhancement and correction"
        icon={<Sparkles size={20} />}
      >
        <ToggleSwitch
          label="Enable Post-Processing"
          name="WHISPER_POST_PROCESSING_ENABLED"
          checked={localConfig.WHISPER_POST_PROCESSING_ENABLED}
          onChange={(value) => handleFieldChange('WHISPER_POST_PROCESSING_ENABLED', value)}
        />
        <SelectInput
          label="Processing Mode"
          name="WHISPER_POST_PROCESSING_MODE"
          value={localConfig.WHISPER_POST_PROCESSING_MODE}
          onChange={(value) => handleFieldChange('WHISPER_POST_PROCESSING_MODE', value)}
          options={POST_PROCESSING_MODES}
        />
        <SelectInput
          label="Processing Trigger"
          name="WHISPER_POST_PROCESSING_TRIGGER"
          value={localConfig.WHISPER_POST_PROCESSING_TRIGGER}
          onChange={(value) => handleFieldChange('WHISPER_POST_PROCESSING_TRIGGER', value)}
          options={POST_PROCESSING_TRIGGERS}
        />
      </Section>
    </div>
  );
}

export function ConfigurationPanel() {
  const api = useWhisperApi();

  if (!api.config) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin text-2xl">⟳</div>
      </div>
    );
  }

  const handleResetToDefaults = async () => {
    const response = await fetch('/api/config/defaults');
    if (!response.ok) {
      throw new Error('Failed to fetch default configuration');
    }
    const defaults = await response.json() as WhisperConfig;
    await api.saveConfig(defaults);
  };

  return (
    <ConfigPanel
      config={api.config}
      onChange={api.setConfig}
      onSave={async () => {
        if (api.config) {
          await api.saveConfig(api.config);
        }
      }}
      onReset={handleResetToDefaults}
      isSaving={false}
      isResetting={false}
      error={api.error}
    />
  );
}
