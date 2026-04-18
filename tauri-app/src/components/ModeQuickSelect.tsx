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
            variant={isActive ? 'default' : 'outline'}
            onClick={() => onModeChange(mode.value)}
            disabled={disabled}
            className="flex flex-col gap-1 h-14"
          >
            <span className="text-lg">{mode.emoji}</span>
            <span className="text-[10px] font-medium">{mode.label}</span>
          </Button>
        );
      })}
    </div>
  );
}
