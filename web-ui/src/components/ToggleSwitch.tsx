interface ToggleSwitchProps {
  label: string;
  name: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  error?: string;
}

export function ToggleSwitch({
  label,
  name,
  checked,
  onChange,
  disabled = false,
  className = '',
  error = '',
}: ToggleSwitchProps) {
  const inputId = `input-${name}`;

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      <label htmlFor={inputId} className="w-1/3 text-gray-400 font-medium text-sm">
        {label}
      </label>
      <div className="flex-1 relative">
        <button
          type="button"
          id={inputId}
          name={name}
          role="switch"
          aria-checked={checked}
          onClick={() => !disabled && onChange(!checked)}
          disabled={disabled}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
            checked ? 'bg-blue-600' : 'bg-gray-600'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ease-in-out ${
              checked ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
        {error && (
          <div className="mt-1 text-red-400 text-xs flex items-center gap-1">
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
