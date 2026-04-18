interface TextInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  description?: string;
  type?: 'text' | 'password' | 'email' | 'url';
}

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
  disabled = false,
  description,
  type = 'text',
}: TextInputProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-slate-900 dark:text-slate-100">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="
          w-full rounded-lg border border-slate-300 bg-white px-3 py-2
          text-sm text-slate-900 shadow-sm transition-colors
          focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20
          dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100
          disabled:cursor-not-allowed disabled:opacity-50
        "
      />
      {description && (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {description}
        </p>
      )}
    </div>
  );
}
