import { AlertCircle } from 'lucide-react';

interface NumericInputProps {
  label: string;
  name: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  error?: string;
}

export function NumericInput({
  label,
  name,
  value,
  onChange,
  min = -Infinity,
  max = Infinity,
  step = 1,
  unit = '',
  required = false,
  disabled = false,
  className = '',
  error = '',
}: NumericInputProps) {
  const inputId = `input-${name}`;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseFloat(e.target.value);
    if (!isNaN(newValue)) {
      onChange(newValue);
    }
  };

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      <label htmlFor={inputId} className="w-1/3 text-gray-400 font-medium text-sm">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      <div className="flex-1 relative">
        <div className="flex items-center">
          <input
            id={inputId}
            type="number"
            name={name}
            value={value}
            onChange={handleChange}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            className={`flex-1 px-3 py-2 rounded-l-lg bg-gray-700 text-white placeholder-gray-500 border-2 border-r-0 transition-all ${
              error
                ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
                : 'border-gray-600 focus:ring-blue-500 focus:border-blue-500'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          />
          {unit && (
            <span className="px-3 py-2 rounded-r-lg bg-gray-700 text-gray-400 border-2 border-l-0 border-gray-600 font-mono text-sm">
              {unit}
            </span>
          )}
        </div>
        {error && (
          <div className="flex items-center gap-1 mt-1 text-red-400 text-xs">
            <AlertCircle size={12} />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
