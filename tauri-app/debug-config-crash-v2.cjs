/**
 * Precise config crash reproducer with Tauri mock.
 * Catches the exact error that crashes the config tab.
 */
const { chromium } = require('playwright');

const RUST_CONFIG = {
  whisper_cli: "whisper-cli",
  model: "/home/jon/.local/share/whisper-hotkey/models/ggml-base.en.bin",
  source: "",
  preferred_sources: "",
  chunk_seconds: 3.5,
  overlap_seconds: 0.8,
  type_delay_ms: 1,
  language: "en",
  suppress_regex: "[,.]",
  suppress_nst: true,
  smart_punctuation: true,
  symbol_words_to_symbols: false,
  direct_streaming: false,
  log_file: "/tmp/whisper_hotkey.log",
  log_level: "info",
  voice_activation_mode: "toggle",
  post_processing_enabled: false,
  post_processing_mode: "off",
  post_processing_trigger: "auto_long",
  indicator_enabled: true,
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 300, height: 420 } });
  const page = await ctx.newPage();

  const errors = [];
  page.on('console', msg => {
    const text = msg.text();
    console.log(`[${msg.type()}] ${text.substring(0, 300)}`);
    if (msg.type() === 'error') errors.push(text);
  });
  page.on('pageerror', err => {
    console.log(`[PAGE ERROR] ${err.message}\n${err.stack?.substring(0, 500)}`);
    errors.push(err.message);
  });

  // Inject Tauri mock BEFORE page load
  await page.addInitScript((config) => {
    window.__TAURI_INTERNALS__ = {
      invoke: (cmd, args) => {
        console.log('[MOCK invoke]', cmd);
        if (cmd === 'get_config') return Promise.resolve(config);
        if (cmd === 'get_status') return Promise.resolve({ is_running: false, stream_text: '' });
        if (cmd === 'set_config') return Promise.resolve();
        if (cmd === 'list_sources') return Promise.resolve([]);
        return Promise.resolve({});
      },
      convertFileSrc: (p) => p,
      metadata: { currentWindow: { label: 'main' } },
    };
  }, RUST_CONFIG);

  // Route Tauri plugin imports to prevent crashes from missing modules
  await page.route('**/@tauri-apps/**', route => {
    console.log('[ROUTE BLOCKED]', route.request().url());
    route.fulfill({ status: 200, body: 'export default {};', contentType: 'text/javascript' });
  });

  await page.goto('http://localhost:8099', { waitUntil: 'networkidle' }).catch(e => {
    console.log('[GOTO ERROR]', e.message.substring(0, 200));
  });
  await page.waitForTimeout(2000);

  // Check if page is still alive
  let pageAlive = true;
  try {
    const title = await page.title();
    console.log('Page title:', title);
  } catch (e) {
    console.log('PAGE IS DEAD after initial load:', e.message.substring(0, 200));
    pageAlive = false;
  }

  if (pageAlive) {
    // Use evaluate to click config tab (safer than Playwright click)
    const clickResult = await page.evaluate(() => {
      try {
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
          if (btn.textContent?.includes('Config')) {
            btn.click();
            return 'clicked config';
          }
        }
        return 'config button not found';
      } catch (e) {
        return 'CLICK ERROR: ' + e.message;
      }
    });
    console.log('Click result:', clickResult);

    // Wait and check if page survived
    await page.waitForTimeout(3000);

    try {
      const afterClick = await page.evaluate(() => {
        const root = document.getElementById('root');
        return {
          alive: true,
          text: root?.textContent?.substring(0, 500),
          hasError: root?.textContent?.includes('Something went wrong') || root?.textContent?.includes('Failed to load'),
          details: document.querySelectorAll('details').length,
        };
      });
      console.log('After click:', JSON.stringify(afterClick, null, 2));
    } catch (e) {
      console.log('PAGE DIED after config click:', e.message.substring(0, 300));
    }
  }

  console.log('\n=== ALL ERRORS ===');
  errors.forEach(e => console.log(e));

  await browser.close().catch(() => {});
  process.exit(0);
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
