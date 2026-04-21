/**
 * Simulate actual Tauri runtime to reproduce config tab crash.
 * Sets __TAURI_INTERNALS__ and mocks invoke() to return real Rust WhisperConfig shape.
 */
const { chromium } = require('playwright');

// Exact shape Rust WhisperConfig serializes to JSON via serde
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
  log_level: "info",                    // ← Rust has this, TypeScript interface does NOT
  voice_activation_mode: "toggle",       // serde rename_all snake_case
  post_processing_enabled: false,
  post_processing_mode: "off",           // serde rename_all snake_case
  post_processing_trigger: "auto_long",  // ← NOTE: underscore, TypeScript expects "auto-long" (hyphen)
  indicator_enabled: true,
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 300, height: 420 },
  });
  const page = await ctx.newPage();

  const errors = [];
  const consoleMsgs = [];
  page.on('console', msg => {
    consoleMsgs.push({ type: msg.type(), text: msg.text() });
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => {
    errors.push('[PAGE ERROR] ' + err.message + '\n' + err.stack);
  });

  // Inject Tauri internals BEFORE page loads
  await page.addInitScript((config) => {
    // Simulate Tauri runtime
    window.__TAURI_INTERNALS__ = {
      invoke: (cmd, args) => {
        console.log('[MOCK INVOKE]', cmd, JSON.stringify(args));
        if (cmd === 'get_config') return Promise.resolve(config);
        if (cmd === 'get_status') return Promise.resolve({ is_running: false, stream_text: '' });
        if (cmd === 'set_config') {
          console.log('[MOCK SET_CONFIG]', JSON.stringify(args.config));
          return Promise.resolve();
        }
        if (cmd === 'list_sources') return Promise.resolve([]);
        return Promise.resolve({});
      },
      convertFileSrc: (path) => path,
      metadata: { currentWindow: { label: 'main' } },
    };

    // Mock @tauri-apps/api
    window.__TAURI_API_MOCK__ = true;
  }, RUST_CONFIG);

  // Also mock the ES module imports
  await page.addInitScript(() => {
    // Intercept dynamic imports for Tauri plugins
    const origFetch = window.fetch;
  });

  await page.goto('http://localhost:8099', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  console.log('=== PHASE 1: INITIAL LOAD (Tauri context) ===');
  const initial = await page.evaluate(() => {
    const root = document.getElementById('root');
    return {
      text: root?.textContent?.substring(0, 300),
      hasTauriInternals: !!window.__TAURI_INTERNALS__,
      childCount: root?.children?.length,
    };
  });
  console.log('Has Tauri internals:', initial.hasTauriInternals);
  console.log('Initial text:', initial.text);

  // Click Config tab
  const buttons = await page.$$('button');
  let configBtn = null;
  for (const btn of buttons) {
    const text = await btn.textContent();
    if (text && text.includes('Config')) {
      configBtn = btn;
      break;
    }
  }

  if (configBtn) {
    console.log('\n=== PHASE 2: CLICKING CONFIG TAB ===');
    await configBtn.click();
    await page.waitForTimeout(2000);

    const configState = await page.evaluate(() => {
      const root = document.getElementById('root');
      const allText = root?.textContent || '';
      
      // Check for React error boundary
      const errorBoundary = allText.includes('Something went wrong');
      
      // Check for our fallback
      const failedLoad = allText.includes('Failed to load');
      
      // Check for config panel structure
      const details = root?.querySelectorAll('details');
      const scrollContainers = root?.querySelectorAll('.scroll-container');
      
      // Check for the PostProcessingTrigger select value
      const triggerSelect = root?.querySelector('[id="post-processing-trigger"]');
      const triggerSelectValue = triggerSelect?.textContent;
      
      // Check PostProcessingGrid
      const modeGrid = root?.querySelector('[class*="grid"]');
      
      // Get all error-colored text
      const destructiveEls = root?.querySelectorAll('.text-destructive');
      const destructiveTexts = Array.from(destructiveEls || []).map(e => e.textContent);

      return {
        fullText: allText.substring(0, 1500),
        errorBoundary,
        failedLoad,
        detailsCount: details?.length || 0,
        scrollContainerCount: scrollContainers?.length || 0,
        triggerSelectValue,
        hasModeGrid: !!modeGrid,
        destructiveTexts,
      };
    });

    console.log('Full text:', configState.fullText);
    console.log('Error boundary:', configState.errorBoundary);
    console.log('Failed load:', configState.failedLoad);
    console.log('Details count:', configState.detailsCount);
    console.log('Scroll containers:', configState.scrollContainerCount);
    console.log('Trigger select value:', configState.triggerSelectValue);
    console.log('Has mode grid:', configState.hasModeGrid);
    console.log('Destructive texts:', configState.destructiveTexts);

    // Try interacting with the trigger select
    console.log('\n=== PHASE 3: INTERACT WITH TRIGGER SELECT ===');
    const triggerResult = await page.evaluate(() => {
      // Try to open the PostProcessing section
      const details = document.querySelectorAll('details');
      for (const d of details) {
        const summary = d.querySelector('summary');
        if (summary?.textContent?.includes('Post-Processing')) {
          d.open = true;
        }
      }
      return 'opened post-processing section';
    });
    await page.waitForTimeout(500);

    // Try clicking the trigger select
    const triggerSelectEl = await page.$('#post-processing-trigger');
    if (triggerSelectEl) {
      try {
        await triggerSelectEl.click();
        await page.waitForTimeout(1000);
        console.log('Trigger select clicked successfully');
        
        // Check if dropdown opened
        const dropdownState = await page.evaluate(() => {
          const selectContent = document.querySelector('[role="listbox"]');
          return {
            hasListbox: !!selectContent,
            listboxText: selectContent?.textContent,
          };
        });
        console.log('Dropdown state:', JSON.stringify(dropdownState));
      } catch (e) {
        console.log('TRIGGER SELECT CLICK FAILED:', e.message);
      }
    } else {
      console.log('Trigger select element NOT FOUND');
    }
  }

  console.log('\n=== CONSOLE MESSAGES ===');
  for (const msg of consoleMsgs) {
    if (msg.type === 'error' || msg.type === 'warning' || msg.text.includes('[MOCK')) {
      console.log(`[${msg.type}] ${msg.text.substring(0, 200)}`);
    }
  }

  console.log('\n=== ALL ERRORS ===');
  for (const err of errors) {
    console.log(err);
  }

  await browser.close();
  process.exit(errors.length > 0 ? 1 : 0);
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
