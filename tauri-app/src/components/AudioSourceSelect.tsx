import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface AudioSource {
  id: string;
  name: string;
}

interface AudioSourceSelectProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function AudioSourceSelect({ value, onChange, disabled = false }: AudioSourceSelectProps) {
  const [sources, setSources] = useState<AudioSource[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSources = async () => {
      try {
        const result = await invoke<string[]>('list_sources');
        const audioSources: AudioSource[] = result.map((name) => ({
          id: name,
          name: name,
        }));
        setSources(audioSources);

        if (!value && audioSources.length > 0) {
          onChange(audioSources[0].id);
        }
      } catch (err) {
        console.error('Failed to load audio sources:', err);
      } finally {
        setLoading(false);
      }
    };

    loadSources();
  }, [value, onChange]);

  if (loading) {
    return (
      <Select disabled value={value}>
        <SelectTrigger>
          <SelectValue placeholder="Loading..." />
        </SelectTrigger>
      </Select>
    );
  }

  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger>
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
