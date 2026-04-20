import { useState, useEffect } from 'react';
import { open } from '@tauri-apps/plugin-dialog';
import { homeDir } from '@tauri-apps/api/path';
import { Input } from './ui/input';
import { cn } from '@/lib/utils';

const isTauri = (): boolean => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

async function expandTilde(path: string): Promise<string> {
  if (!isTauri()) return path;
  const home = await homeDir();
  return home ? home + path.slice(1) : path;
}

async function shortenToTilde(path: string): Promise<string> {
  if (!isTauri()) return path;
  const home = await homeDir();
  return home && path.startsWith(home) ? '~' + path.slice(home.length) : path;
}

interface FilePickerInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  id?: string;
}

export function FilePickerInput({ value, onChange, placeholder, label, id }: FilePickerInputProps) {
  const [displayValue, setDisplayValue] = useState<string>(value);

  useEffect(() => {
    setDisplayValue(value);
  }, [value]);

  const handleBrowse = async () => {
    if (!isTauri()) return;
    try {
      const selected = await open({
        multiple: false,
        directory: false,
      });
      if (selected && typeof selected === 'string') {
        onChange(selected);
        setDisplayValue(await shortenToTilde(selected));
      }
    } catch (err) {
      console.error('Failed to open file picker:', err);
    }
  };

  return (
    <div className="flex gap-1">
      <Input
        id={id}
        value={displayValue}
        onChange={async (e) => {
          const newValue = e.target.value;
          setDisplayValue(newValue);
          try {
            if (newValue.startsWith('~/')) {
              onChange(await expandTilde(newValue));
            } else {
              onChange(newValue);
            }
          } catch {
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
