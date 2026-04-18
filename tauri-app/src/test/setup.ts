import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as React from 'react';

afterEach(() => {
  cleanup();
});

// Mock pointer capture APIs for Radix UI Select (jsdom doesn't implement these)
HTMLElement.prototype.hasPointerCapture = HTMLElement.prototype.hasPointerCapture || vi.fn().mockReturnValue(false);
HTMLElement.prototype.setPointerCapture = HTMLElement.prototype.setPointerCapture || vi.fn();
HTMLElement.prototype.releasePointerCapture = HTMLElement.prototype.releasePointerCapture || vi.fn();

// Mock scrollIntoView for Radix UI (jsdom doesn't implement this)
HTMLElement.prototype.scrollIntoView = HTMLElement.prototype.scrollIntoView || vi.fn();

const mockInvoke = vi.fn();
const mockListen = vi.fn().mockResolvedValue(vi.fn());

vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => mockInvoke(...args),
}));

vi.mock('@tauri-apps/api/event', () => ({
  listen: (...args: unknown[]) => mockListen(...args),
}));

vi.mock('@tauri-apps/plugin-opener', () => ({
  open: vi.fn(),
}));

vi.mock('lucide-react', () => ({
  Check: (props: any) => React.createElement('svg', { ...props, 'data-testid': 'lucide-check' }),
  ChevronDown: (props: any) => React.createElement('svg', { ...props, 'data-testid': 'lucide-chevron-down' }),
  ChevronUp: (props: any) => React.createElement('svg', { ...props, 'data-testid': 'lucide-chevron-up' }),
}));

export { mockInvoke, mockListen };
