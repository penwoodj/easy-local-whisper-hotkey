import { useEffect, useState, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

const isTauri = (): boolean => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

interface AudioSource {
  id: string;
  name: string;
}

interface AudioSourceSelectProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  id?: string;
}

export function AudioSourceSelect({ value, onChange, disabled = false, id }: AudioSourceSelectProps) {
  const [sources, setSources] = useState<AudioSource[]>([]);
  const [loading, setLoading] = useState(true);
  const onChangeRef = useRef(onChange);
  const valueRef = useRef(value);

  // Keep refs current without triggering re-renders
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  // Load sources once on mount
  useEffect(() => {
    let cancelled = false;

    const loadSources = async () => {
      if (!isTauri()) {
        setLoading(false);
        return;
      }
      try {
        const result = await invoke<string[]>('list_sources');
        if (cancelled) return;

        // Validate result is an array
        if (!Array.isArray(result)) {
          console.error('list_sources returned non-array:', typeof result);
          setSources([]);
          setLoading(false);
          return;
        }

        const audioSources: AudioSource[] = result.map((name) => ({
          id: name,
          name: name,
        }));
        setSources(audioSources);

        // Auto-select first source if none selected
        if (!valueRef.current && audioSources.length > 0) {
          onChangeRef.current(audioSources[0].id);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load audio sources:', err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadSources();

    return () => {
      cancelled = true;
    };
  }, []); // Empty deps — run once on mount

  if (loading || sources.length === 0) {
    return (
      <Select disabled value="">
        <SelectTrigger id={id}>
          <SelectValue placeholder={loading ? 'Loading...' : 'No audio sources found'} />
        </SelectTrigger>
      </Select>
    );
  }

  const validValue = sources.some(s => s.id === value) ? value : undefined;

  return (
    <Select value={validValue} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger id={id}>
        <SelectValue placeholder="Select audio source" />
      </SelectTrigger>
      <SelectContent>
        {sources.map((source) => (
          <SelectItem key={source.id} value={source.id}>
            {source.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
