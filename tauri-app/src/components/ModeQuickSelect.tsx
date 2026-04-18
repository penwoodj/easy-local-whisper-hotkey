import type { PostProcessingMode } from '../types/whisper';
import { Button } from './ui/button';

const MODES: { value: PostProcessingMode; emoji: string; label: string }[] = [
  { value: 'off', emoji: '🎙️', label: 'Off' },
  { value: 'light', emoji: '✨', label: 'Light' },
  { value: 'aggressive', emoji: '🔥', label: 'Aggressive' },
  { value: 'agentic', emoji: '🤖', label: 'Agentic' },
  { value: 'writing', emoji: '✍️', label: 'Writing' },
  { value: 'code', emoji: '💻', label: 'Code' },
  { value: 'structure', emoji: '🏗️', label: 'Structure' },
  { value: 'persona', emoji: '👤', label: 'Persona' },
  { value: 'clarity', emoji: '💎', label: 'Clarity' },
];

const MODE_DESCRIPTIONS: Record<string, string> = {
  'off': 'No processing',
  'light': 'Punctuation only',
  'aggressive': 'Full grammar fix',
  'agentic': 'AI-powered rewrite',
  'writing': 'Prose optimization',
  'code': 'Code formatting',
  'structure': 'Text restructuring',
  'persona': 'Tone adjustment',
  'clarity': 'Readability boost',
};

interface ModeQuickSelectProps {
  currentMode: PostProcessingMode;
  onModeChange: (mode: PostProcessingMode) => void;
  disabled?: boolean;
}

export function ModeQuickSelect({
  currentMode,
  onModeChange,
  disabled = false,
}: ModeQuickSelectProps) {
  return (
    <div className="grid grid-cols-3 gap-2 sm:gap-2.5" role="radiogroup" aria-label="Post-processing mode selection">
      {MODES.map((mode) => {
        const isActive = currentMode === mode.value;

        return (
          <Button
            key={mode.value}
            variant="outline"
            onClick={() => onModeChange(mode.value)}
            disabled={disabled}
            className={`
              flex flex-col gap-1 h-auto py-3 transition-all
              ${isActive
                ? 'border-2 border-primary bg-transparent ring-2 ring-primary/30 shadow-md shadow-primary/20 text-primary'
                : 'border border-border bg-card hover:bg-card/80 text-foreground hover:ring-2 hover:ring-primary/20 hover:border-primary/50'
              }
            `}
          >
            <span className="text-lg">{mode.emoji}</span>
            <span className="text-[10px] font-medium">{mode.label}</span>
            <span className="text-[10px] text-muted-foreground">{MODE_DESCRIPTIONS[mode.value]}</span>
          </Button>
        );
      })}
    </div>
  );
}
