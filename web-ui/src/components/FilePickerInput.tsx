import { FolderOpen, AlertCircle } from 'lucide-react';

interface FilePickerInputProps {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  error?: string;
}

export function FilePickerInput({
  label,
  name,
  value,
  onChange,
  placeholder = '',
  required = false,
  disabled = false,
  className = '',
  error = '',
}: FilePickerInputProps) {
  const inputId = `input-${name}`;

  const handleBrowse = async () => {
    try {
      // In a real implementation, this would open a file dialog
      // For now, we'll just focus the input
      const input = document.getElementById(inputId) as HTMLInputElement;
      if (input) {
        input.focus();
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err);
    }
  };

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      <label htmlFor={inputId} className="w-1/3 text-gray-400 font-medium text-sm">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      <div className="flex-1 relative">
        <div className="flex items-center gap-2">
          <input
            id={inputId}
            type="text"
            name={name}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            className={`flex-1 px-3 py-2 rounded-l-lg bg-gray-700 text-white placeholder-gray-500 border-2 border-r-0 transition-all ${
              error
                ? 'border-red-500 focus:ring-red-500 focus:border-red-500'
                : 'border-gray-600 focus:ring-blue-500 focus:border-blue-500'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          />
          <button
            type="button"
            onClick={handleBrowse}
            disabled={disabled}
            className={`px-4 py-2 rounded-r-lg bg-gray-700 text-gray-300 border-2 border-l-0 border-gray-600 hover:bg-gray-600 transition-all ${
              error ? 'border-red-500' : 'border-gray-600'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            title="Browse"
          >
            <FolderOpen size={16} />
          </button>
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
