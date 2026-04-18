export type PostProcessingMode =
  | 'off'
  | 'light'
  | 'aggressive'
  | 'agentic'
  | 'writing'
  | 'code'
  | 'structure'
  | 'persona'
  | 'clarity';

export type PostProcessingTrigger = 'always' | 'manual' | 'auto-long' | 'preview';

export type VoiceActivationMode = 'hold' | 'toggle';

export interface FilterRule {
  id: string;
  name: string;
  pattern: string;
  enabled: boolean;
  is_builtin: boolean;
}

export interface WhisperConfig {
  whisper_cli: string;
  model: string;
  source: string;
  preferred_sources: string;
  chunk_seconds: number;
  overlap_seconds: number;
  type_delay_ms: number;
  language: string;
  suppress_regex: string;
  suppress_nst: boolean;
  smart_punctuation: boolean;
  symbol_words_to_symbols: boolean;
  direct_streaming: boolean;
  log_file: string;
  post_processing_enabled: boolean;
  post_processing_mode: PostProcessingMode;
  post_processing_trigger: PostProcessingTrigger;
  voice_activation_mode: VoiceActivationMode;
  indicator_enabled: boolean;
}

export interface WhisperStatus {
  is_running: boolean;
  pid?: number;
  last_started?: string;
  stream_text: string;
}

export interface AudioSource {
  name: string;
  description?: string;
  is_default: boolean;
}

export interface StreamingTextEvent {
  text: string;
  timestamp: string;
  is_final: boolean;
}

export interface DiagnosticInfo {
  display: string;
  xauthority: string;
  model_path: string;
  model_exists: boolean;
  whisper_cli_path: string;
  whisper_cli_exists: boolean;
  commands: {
    parec: boolean;
    pactl: boolean;
    xdotool: boolean;
  };
  preferred_sources: string[];
  default_source: string;
  available_sources: string[];
  source_error: string;
  requested_source: string;
  chunk_seconds: number;
  overlap_seconds: number;
  type_delay_ms: number;
  language: string;
  suppress_regex: string;
  suppress_nst: boolean;
  smart_punctuation: boolean;
  symbol_words_to_symbols: boolean;
  direct_streaming: boolean;
  log_file: string;
  resolved_source?: string;
  resolved_source_error?: string;
  healthy: boolean;
  version: string;
}

export type TauriCommand =
  | 'start_daemon'
  | 'stop_daemon'
  | 'get_config'
  | 'set_config'
  | 'get_status'
  | 'list_sources'
  | 'get_diagnostics'
  | 'test_recording';

export type TauriEvent =
  | 'streaming-text'
  | 'daemon-started'
  | 'daemon-stopped'
  | 'error';
