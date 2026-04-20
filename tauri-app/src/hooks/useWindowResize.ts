import { getCurrentWindow } from '@tauri-apps/api/window';
import { LogicalSize } from '@tauri-apps/api/dpi';

const isTauri = (): boolean => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

const TAB_SIZES: Record<string, { width: number; height: number }> = {
  status: { width: 300, height: 420 },
  modes: { width: 300, height: 480 },
  config: { width: 300, height: 680 },
};

export async function resizeWindowForTab(tab: string) {
  if (!isTauri()) return;
  try {
    const size = TAB_SIZES[tab] || TAB_SIZES.status;
    const appWindow = getCurrentWindow();
    await appWindow.setSize(new LogicalSize(size.width, size.height));
  } catch (e) {
    // Silently ignore — window API may not be ready during init
  }
}
