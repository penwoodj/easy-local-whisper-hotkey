import { useState, useEffect } from 'react';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import type { FilterRule } from '../types/whisper';

const DEFAULT_RULES: FilterRule[] = [
  {
    id: 'builtin-filler',
    name: 'Remove filler words',
    pattern: 'um|uh|ah|er|hmm',
    enabled: true,
    is_builtin: true,
  },
  {
    id: 'builtin-repeated',
    name: 'Remove repeated words',
    pattern: '\\b(\\w+)\\s+\\1\\b',
    enabled: false,
    is_builtin: true,
  },
  {
    id: 'builtin-timestamps',
    name: 'Clean timestamps',
    pattern: '\\d{1,2}:\\d{2}(?::\\d{2})?',
    enabled: false,
    is_builtin: true,
  },
];

interface RulesManagerProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

function parseRules(jsonString: string): FilterRule[] {
  if (!jsonString.trim()) {
    return DEFAULT_RULES.map(r => ({ ...r }));
  }

  try {
    const parsed = JSON.parse(jsonString);
    if (Array.isArray(parsed)) {
      return parsed.filter(
        (item): item is FilterRule =>
          item != null &&
          typeof item === 'object' &&
          typeof item.id === 'string' &&
          typeof item.name === 'string' &&
          typeof item.pattern === 'string' &&
          typeof item.enabled === 'boolean'
      );
    }

    if (typeof parsed === 'string') {
      return [
        {
          id: 'legacy-regex',
          name: 'Legacy regex',
          pattern: parsed,
          enabled: true,
          is_builtin: false,
        },
      ];
    }

    return DEFAULT_RULES.map(r => ({ ...r }));
  } catch {
    if (jsonString.trim()) {
      return [
        {
          id: 'legacy-regex',
          name: 'Legacy regex',
          pattern: jsonString,
          enabled: true,
          is_builtin: false,
        },
      ];
    }
    return DEFAULT_RULES.map(r => ({ ...r }));
  }
}

export function RulesManager({ value, onChange, disabled = false }: RulesManagerProps) {
  const [rules, setRules] = useState<FilterRule[]>(() => parseRules(value));
  const [newRuleName, setNewRuleName] = useState('');
  const [newRulePattern, setNewRulePattern] = useState('');

  useEffect(() => {
    if (rules.length === 0 || (rules.length === DEFAULT_RULES.length && rules.every((r, i) => r.id === DEFAULT_RULES[i].id && r.enabled === DEFAULT_RULES[i].enabled))) {
      return;
    }
    onChange(JSON.stringify(rules));
  }, [rules, onChange]);

  const toggleRule = (id: string) => {
    setRules(prev => prev.map(rule =>
      rule.id === id ? { ...rule, enabled: !rule.enabled } : rule
    ));
  };

  const deleteRule = (id: string) => {
    setRules(prev => prev.filter(rule => rule.id !== id));
  };

  const addRule = () => {
    if (!newRuleName.trim() || !newRulePattern.trim()) {
      return;
    }

    const newRule: FilterRule = {
      id: `custom-${Date.now()}`,
      name: newRuleName.trim(),
      pattern: newRulePattern.trim(),
      enabled: true,
      is_builtin: false,
    };

    setRules(prev => [...prev, newRule]);
    setNewRuleName('');
    setNewRulePattern('');
  };

  return (
    <div className="space-y-2">
      <div className="space-y-1">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="flex items-center gap-2 p-2 border border-border bg-card rounded"
          >
            <Switch
              checked={rule.enabled}
              onCheckedChange={() => toggleRule(rule.id)}
              disabled={disabled}
              className="h-5 w-9"
            />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium truncate">{rule.name}</div>
              <code className="text-[10px] text-muted-foreground font-mono truncate block">
                {rule.pattern}
              </code>
            </div>
            {!rule.is_builtin && (
              <button
                type="button"
                onClick={() => deleteRule(rule.id)}
                disabled={disabled}
                className="text-xs text-destructive hover:text-destructive/80 px-2 py-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Delete
              </button>
            )}
          </div>
        ))}
      </div>

      {!disabled && (
        <div className="flex gap-1">
          <Input
            value={newRuleName}
            onChange={(e) => setNewRuleName(e.target.value)}
            placeholder="Rule name"
            className="h-7 text-xs flex-1"
          />
          <Input
            value={newRulePattern}
            onChange={(e) => setNewRulePattern(e.target.value)}
            placeholder="Regex pattern"
            className="h-7 text-xs flex-1 font-mono"
          />
          <button
            type="button"
            onClick={addRule}
            disabled={!newRuleName.trim() || !newRulePattern.trim()}
            className="h-7 px-3 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add
          </button>
        </div>
      )}
    </div>
  );
}
