export type PostProcessingMode = 'off' | 'light' | 'aggressive' | 'agentic' | 'writing' | 'code' | 'structure' | 'persona' | 'clarity';
export type PostProcessingTrigger = 'always' | 'manual' | 'auto_long' | 'preview';
export type VoiceActivationMode = 'hold' | 'toggle';

export interface WhisperConfig {
  WHISPER_CLI: string;
  WHISPER_MODEL: string;
  WHISPER_AUDIO_SOURCE: string;
  WHISPER_PREFERRED_SOURCES: string;
  WHISPER_CHUNK_SECONDS: number;
  WHISPER_OVERLAP_SECONDS: number;
  WHISPER_TYPE_DELAY_MS: number;
  WHISPER_LANGUAGE: string;
  WHISPER_SUPPRESS_REGEX: string;
  WHISPER_SUPPRESS_NST: boolean;
  WHISPER_SMART_PUNCTUATION: boolean;
  WHISPER_SYMBOL_WORDS_TO_SYMBOLS: boolean;
  WHISPER_DIRECT_STREAMING: boolean;
  WHISPER_LOG_FILE: string;
  WHISPER_LOG_LEVEL: string;
  WHISPER_ACTIVATION_MODE: VoiceActivationMode;
  WHISPER_POST_PROCESSING_ENABLED: boolean;
  WHISPER_POST_PROCESSING_MODE: PostProcessingMode;
  WHISPER_POST_PROCESSING_TRIGGER: PostProcessingTrigger;
  WHISPER_INDICATOR: boolean;
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
