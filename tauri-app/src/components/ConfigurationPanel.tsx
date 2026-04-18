import { useState } from 'react';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Switch } from './ui/switch';
import type {
  WhisperConfig,
  PostProcessingMode,
  PostProcessingTrigger,
  VoiceActivationMode,
} from '../types/whisper';

interface ConfigurationPanelProps {
  config: WhisperConfig;
  onConfigChange: (config: WhisperConfig) => void;
  disabled?: boolean;
}

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'nl', label: 'Dutch' },
  { value: 'ru', label: 'Russian' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
] as const;

const POST_PROCESSING_MODES: { value: PostProcessingMode; label: string }[] = [
  { value: 'off', label: 'Off' },
  { value: 'light', label: 'Light' },
  { value: 'aggressive', label: 'Aggressive' },
  { value: 'agentic', label: 'Agentic' },
  { value: 'writing', label: 'Writing' },
  { value: 'code', label: 'Code' },
  { value: 'structure', label: 'Structure' },
  { value: 'persona', label: 'Persona' },
  { value: 'clarity', label: 'Clarity' },
];

const POST_PROCESSING_TRIGGERS: { value: PostProcessingTrigger; label: string }[] = [
  { value: 'always', label: 'Always' },
  { value: 'manual', label: 'Manual' },
  { value: 'auto-long', label: 'Auto Long' },
  { value: 'preview', label: 'Preview' },
];

const VOICE_ACTIVATION_MODES: { value: VoiceActivationMode; label: string }[] = [
  { value: 'hold', label: 'Hold' },
  { value: 'toggle', label: 'Toggle' },
];

interface CollapsibleSectionProps {
  title: string;
  defaultOpen: boolean;
  children: React.ReactNode;
}

function CollapsibleSection({ title, defaultOpen, children }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <details open={isOpen} onToggle={(e) => setIsOpen(e.currentTarget.open)} className="group">
      <summary className="cursor-pointer list-none select-none text-sm font-semibold text-foreground hover:text-primary">
        <span className="inline-block transition-transform group-open:rotate-90">
          {isOpen ? '▶' : '▶'}
        </span>
        {' '}{title}
      </summary>
      <div className={`mt-2 space-y-2 ${isOpen ? 'block' : 'hidden'}`}>
        {children}
      </div>
    </details>
  );
}

export function ConfigurationPanel({ config, onConfigChange, disabled = false }: ConfigurationPanelProps) {
  const updateConfig = (updates: Partial<WhisperConfig>) => {
    onConfigChange({ ...config, ...updates });
  };

  return (
    <div className="space-y-3">
      <CollapsibleSection title="Audio & Transcription" defaultOpen>
        <div className="space-y-2">
          <div className="space-y-1">
            <label htmlFor="whisper-cli" className="text-xs font-medium leading-none">Whisper CLI</label>
            <Input
              id="whisper-cli"
              value={config.whisper_cli}
              onChange={(e) => updateConfig({ whisper_cli: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="model" className="text-xs font-medium leading-none">Model</label>
            <Input
              id="model"
              value={config.model}
              onChange={(e) => updateConfig({ model: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="language" className="text-xs font-medium leading-none">Language</label>
            <Select
              value={config.language}
              onValueChange={(value) => updateConfig({ language: value as any })}
              disabled={disabled}
            >
              <SelectTrigger id="language">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Audio Source" defaultOpen={false}>
        <div className="space-y-2">
          <div className="space-y-1">
            <label htmlFor="audio-source" className="text-xs font-medium leading-none">Source</label>
            <Input
              id="audio-source"
              value={config.source}
              onChange={(e) => updateConfig({ source: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="preferred-sources" className="text-xs font-medium leading-none">Preferred</label>
            <Input
              id="preferred-sources"
              value={config.preferred_sources}
              onChange={(e) => updateConfig({ preferred_sources: e.target.value })}
              disabled={disabled}
            />
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Streaming Behavior" defaultOpen={false}>
        <div className="space-y-2">
          <div className="space-y-1">
            <label htmlFor="chunk-seconds" className="text-xs font-medium leading-none">Chunk (s)</label>
            <Input
              id="chunk-seconds"
              type="number"
              value={config.chunk_seconds}
              onChange={(e) => updateConfig({ chunk_seconds: parseFloat(e.target.value) || 0 })}
              step={0.1}
              disabled={disabled}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="overlap-seconds" className="text-xs font-medium leading-none">Overlap (s)</label>
            <Input
              id="overlap-seconds"
              type="number"
              value={config.overlap_seconds}
              onChange={(e) => updateConfig({ overlap_seconds: parseFloat(e.target.value) || 0 })}
              step={0.1}
              disabled={disabled}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="type-delay" className="text-xs font-medium leading-none">Type Delay (ms)</label>
            <Input
              id="type-delay"
              type="number"
              value={config.type_delay_ms}
              onChange={(e) => updateConfig({ type_delay_ms: parseInt(e.target.value) || 0 })}
              disabled={disabled}
            />
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Features" defaultOpen>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="direct-streaming" className="text-xs font-medium leading-none">Real-time</label>
            <Switch
              id="direct-streaming"
              checked={config.direct_streaming}
              onCheckedChange={(checked) => updateConfig({ direct_streaming: checked })}
              disabled={disabled}
            />
          </div>
          <div className="flex items-center justify-between">
            <label htmlFor="smart-punctuation" className="text-xs font-medium leading-none">Smart Punctuation</label>
            <Switch
              id="smart-punctuation"
              checked={config.smart_punctuation}
              onCheckedChange={(checked) => updateConfig({ smart_punctuation: checked })}
              disabled={disabled}
            />
          </div>
          <div className="flex items-center justify-between">
            <label htmlFor="symbol-words" className="text-xs font-medium leading-none">Symbols</label>
            <Switch
              id="symbol-words"
              checked={config.symbol_words_to_symbols}
              onCheckedChange={(checked) => updateConfig({ symbol_words_to_symbols: checked })}
              disabled={disabled}
            />
          </div>
          <div className="flex items-center justify-between">
            <label htmlFor="suppress-nst" className="text-xs font-medium leading-none">Suppress NST</label>
            <Switch
              id="suppress-nst"
              checked={config.suppress_nst}
              onCheckedChange={(checked) => updateConfig({ suppress_nst: checked })}
              disabled={disabled}
            />
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Post-Processing" defaultOpen={false}>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="post-processing" className="text-xs font-medium leading-none">Enabled</label>
            <Switch
              id="post-processing"
              checked={config.post_processing_enabled}
              onCheckedChange={(checked) => updateConfig({ post_processing_enabled: checked })}
              disabled={disabled}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="post-processing-mode" className="text-xs font-medium leading-none">Mode</label>
            <Select
              value={config.post_processing_mode}
              onValueChange={(value) => updateConfig({ post_processing_mode: value as PostProcessingMode })}
              disabled={disabled || !config.post_processing_enabled}
            >
              <SelectTrigger id="post-processing-mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {POST_PROCESSING_MODES.map((mode) => (
                  <SelectItem key={mode.value} value={mode.value}>
                    {mode.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label htmlFor="post-processing-trigger" className="text-xs font-medium leading-none">Trigger</label>
            <Select
              value={config.post_processing_trigger}
              onValueChange={(value) => updateConfig({ post_processing_trigger: value as PostProcessingTrigger })}
              disabled={disabled || !config.post_processing_enabled}
            >
              <SelectTrigger id="post-processing-trigger">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {POST_PROCESSING_TRIGGERS.map((trigger) => (
                  <SelectItem key={trigger.value} value={trigger.value}>
                    {trigger.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Voice Control" defaultOpen={false}>
        <div className="space-y-2">
          <div className="space-y-1">
            <label htmlFor="voice-activation-mode" className="text-xs font-medium leading-none">Mode</label>
            <Select
              value={config.voice_activation_mode}
              onValueChange={(value) => updateConfig({ voice_activation_mode: value as VoiceActivationMode })}
              disabled={disabled}
            >
              <SelectTrigger id="voice-activation-mode">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VOICE_ACTIVATION_MODES.map((mode) => (
                  <SelectItem key={mode.value} value={mode.value}>
                    {mode.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between">
            <label htmlFor="indicator" className="text-xs font-medium leading-none">Visual Indicator</label>
            <Switch
              id="indicator"
              checked={config.indicator_enabled}
              onCheckedChange={(checked) => updateConfig({ indicator_enabled: checked })}
              disabled={disabled}
            />
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="Advanced" defaultOpen={false}>
        <div className="space-y-2">
          <div className="space-y-1">
            <label htmlFor="suppress-regex" className="text-xs font-medium leading-none">Suppress Regex</label>
            <Input
              id="suppress-regex"
              value={config.suppress_regex}
              onChange={(e) => updateConfig({ suppress_regex: e.target.value })}
              disabled={disabled}
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="log-file" className="text-xs font-medium leading-none">Log File</label>
            <Input
              id="log-file"
              value={config.log_file}
              onChange={(e) => updateConfig({ log_file: e.target.value })}
              disabled={disabled}
            />
          </div>
        </div>
      </CollapsibleSection>
    </div>
  );
}
