import { useState } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { Input } from './ui/input';
import { cn } from '@/lib/utils';

interface FilePickerInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}

export function FilePickerInput({ value, onChange, placeholder, label }: FilePickerInputProps) {
  const [displayValue, setDisplayValue] = useState(() => {
    const homeDir = process.env.HOME || '';
    if (homeDir && value.startsWith(homeDir)) {
      return '~' + value.slice(homeDir.length);
    }
    return value;
  });

  const handleBrowse = async () => {
    try {
      const selected = await open({
        multiple: false,
        directory: false,
      });
      if (selected && typeof selected === 'string') {
        onChange(selected);
        setDisplayValue(() => {
          const homeDir = process.env.HOME || '';
          if (homeDir && selected.startsWith(homeDir)) {
            return '~' + selected.slice(homeDir.length);
          }
          return selected;
        });
      }
    } catch (err) {
      console.error('Failed to open file picker:', err);
    }
  };

  return (
    <div className="flex gap-1">
      <Input
        value={displayValue}
        onChange={(e) => {
          const newValue = e.target.value;
          setDisplayValue(newValue);
          if (newValue.startsWith('~/')) {
            const homeDir = process.env.HOME || '';
            onChange(homeDir + newValue.slice(1));
          } else {
            onChange(newValue);
          }
        }}
        placeholder={placeholder}
        className={cn('h-7 text-xs bg-card border-border', label ? 'flex-1' : '')}
      />
      <button
        type="button"
        onClick={handleBrowse}
        className={cn(
          'h-7 px-2 rounded border border-border bg-card text-foreground',
          'hover:bg-card/80 transition-colors',
          'flex items-center justify-center',
          label ? 'shrink-0' : ''
        )}
        aria-label="Browse for file"
      >
        📂
      </button>
    </div>
  );
}
