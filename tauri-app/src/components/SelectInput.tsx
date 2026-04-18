interface SelectInputProps<T extends string> {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: readonly { value: T; label: string; description?: string }[];
  disabled?: boolean;
  description?: string;
}

export function SelectInput<T extends string>({
  label,
  value,
  onChange,
  options,
  disabled = false,
  description,
}: SelectInputProps<T>) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-slate-900 dark:text-slate-100">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        disabled={disabled}
        className="
          w-full rounded-lg border border-slate-300 bg-white px-3 py-2
          text-sm text-slate-900 shadow-sm transition-colors
          focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20
          dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100
          disabled:cursor-not-allowed disabled:opacity-50
        "
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {description && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {description}
        </p>
      )}
    </div>
  );
}
