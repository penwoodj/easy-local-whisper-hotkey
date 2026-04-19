import { useState, useEffect } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { homeDir } from '@tauri-apps/api/path';
import { Input } from './ui/input';
import { cn } from '@/lib/utils';

interface FilePickerInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}

export function FilePickerInput({ value, onChange, placeholder, label }: FilePickerInputProps) {
  const [displayValue, setDisplayValue] = useState<string>(value);

  useEffect(() => {
    setDisplayValue(value);
  }, [value]);

  const handleBrowse = async () => {
    try {
      const selected = await open({
        multiple: false,
        directory: false,
      });
      if (selected && typeof selected === 'string') {
        onChange(selected);
        const home = await homeDir();
        if (home && selected.startsWith(home)) {
          setDisplayValue('~' + selected.slice(home.length));
        } else {
          setDisplayValue(selected);
        }
      }
    } catch (err) {
      console.error('Failed to open file picker:', err);
    }
  };

  return (
    <div className="flex gap-1">
      <Input
        value={displayValue}
        onChange={async (e) => {
          const newValue = e.target.value;
          setDisplayValue(newValue);
          if (newValue.startsWith('~/')) {
            const home = await homeDir();
            onChange(home + newValue.slice(1));
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
