import { getCurrentWindow } from '@tauri-apps/api/window';
import { PhysicalSize } from '@tauri-apps/api/dpi';

const TAB_SIZES: Record<string, { width: number; height: number }> = {
  status: { width: 280, height: 360 },
  modes: { width: 280, height: 400 },
  config: { width: 280, height: 600 },
};

export async function resizeWindowForTab(tab: string) {
  try {
    const size = TAB_SIZES[tab] || TAB_SIZES.status;
    const appWindow = getCurrentWindow();
    await appWindow.setSize(new PhysicalSize(size.width, size.height));
  } catch (e) {
    console.warn('Window resize failed:', e);
  }
}
