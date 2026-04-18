import type { PostProcessingMode } from '../types/whisper';

interface PostProcessingGridProps {
  value: PostProcessingMode;
  onChange: (value: PostProcessingMode) => void;
  disabled?: boolean;
}

const MODES: { value: PostProcessingMode; icon: string; label: string }[] = [
  { value: 'off', icon: '⊘', label: 'Off' },
  { value: 'light', icon: '✨', label: 'Light' },
  { value: 'aggressive', icon: '⚡', label: 'Aggressive' },
  { value: 'agentic', icon: '🤖', label: 'Agentic' },
  { value: 'writing', icon: '✏️', label: 'Writing' },
  { value: 'code', icon: '💻', label: 'Code' },
  { value: 'structure', icon: '📐', label: 'Structure' },
  { value: 'persona', icon: '🎭', label: 'Persona' },
  { value: 'clarity', icon: '🔍', label: 'Clarity' },
];

export function PostProcessingGrid({ value, onChange, disabled = false }: PostProcessingGridProps) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {MODES.map((mode) => (
        <button
          key={mode.value}
          type="button"
          onClick={() => onChange(mode.value)}
          disabled={disabled}
          className={`
            flex flex-col items-center justify-center gap-1 p-2 rounded transition-all
            ${value === mode.value
              ? 'border-2 border-primary bg-primary/10 ring-1 ring-primary/30 shadow-sm shadow-primary/20'
              : 'border border-border bg-card hover:bg-card/80'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <span className="text-base">{mode.icon}</span>
          <span className="text-[10px]">{mode.label}</span>
        </button>
      ))}
    </div>
  );
}
