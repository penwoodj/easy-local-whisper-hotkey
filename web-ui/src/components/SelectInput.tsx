import { ChevronDown } from 'lucide-react';

interface SelectInputProps<T extends string> {
  label: string;
  name: string;
  value: T;
  onChange: (value: T) => void;
  options: readonly { value: T; label: string }[];
  disabled?: boolean;
  className?: string;
  error?: string;
}

export function SelectInput<T extends string>({
  label,
  name,
  value,
  onChange,
  options,
  disabled = false,
  className = '',
  error = '',
}: SelectInputProps<T>) {
  const inputId = `input-${name}`;

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      <label htmlFor={inputId} className="w-1/3 text-gray-400 font-medium text-sm">
        {label}
      </label>
      <div className="flex-1 relative">
        <div className="relative">
          <select
            id={inputId}
            name={name}
            value={value}
            onChange={(e) => onChange(e.target.value as T)}
            disabled={disabled}
            className={`w-full px-3 py-2 pr-10 rounded-lg bg-gray-700 text-white appearance-none cursor-pointer border-2 transition-all ${
              error
                ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
                : 'border-gray-600 focus:ring-blue-500 focus:border-blue-500'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown
            size={16}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
          />
        </div>
        {error && (
          <div className="mt-1 text-red-400 text-xs">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
