import React, { useState } from 'react';

interface NumericInputProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  description?: string;
  disabled?: boolean;
}

export function NumericInput({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  unit,
  description,
  disabled = false,
}: NumericInputProps) {
  const [inputValue, setInputValue] = useState(value.toString());

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);

    const parsed = parseFloat(newValue);
    if (!isNaN(parsed) && parsed >= min && parsed <= max) {
      onChange(parsed);
    }
  };

  const handleBlur = () => {
    setInputValue(value.toString());
  };

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-slate-900 dark:text-slate-100">
        {label}
      </label>
      <div className="relative flex items-center">
        <input
          type="number"
          value={inputValue}
          onChange={handleChange}
          onBlur={handleBlur}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          className="
            w-full rounded-lg border border-slate-300 bg-white px-3 py-2
            text-sm text-slate-900 shadow-sm transition-colors
            focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20
            dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100
            disabled:cursor-not-allowed disabled:opacity-50
          "
        />
        {unit && (
          <span className="absolute right-3 text-sm text-slate-500 dark:text-slate-400">
            {unit}
          </span>
        )}
      </div>
      {description && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {description}
        </p>
      )}
    </div>
  );
}
