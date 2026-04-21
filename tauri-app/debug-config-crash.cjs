const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 300, height: 420 } });

  const errors = [];
  const warnings = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push('[ERROR] ' + msg.text());
    if (msg.type() === 'warning') warnings.push('[WARN] ' + msg.text());
  });
  page.on('pageerror', err => errors.push('[PAGE ERROR] ' + err.message));

  await page.goto('http://localhost:8099', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Check initial load
  const initialState = await page.evaluate(() => {
    const root = document.getElementById('root');
    return {
      text: root?.textContent?.substring(0, 500),
      childCount: root?.children?.length,
    };
  });
  console.log('=== INITIAL STATE ===');
  console.log('Text:', initialState.text);
  console.log('Children:', initialState.childCount);

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
    await configBtn.click();
    await page.waitForTimeout(2000);

    const configState = await page.evaluate(() => {
      const root = document.getElementById('root');
      const allText = root?.textContent || '';

      const errorEls = root?.querySelectorAll('.text-destructive');
      const errorTexts = Array.from(errorEls || []).map(e => e.textContent);

      const scrollContainers = root?.querySelectorAll('.scroll-container');
      const details = root?.querySelectorAll('details');

      return {
        fullText: allText.substring(0, 1000),
        errorTexts,
        scrollContainerCount: scrollContainers?.length || 0,
        failedLoad: allText.includes('Failed to load'),
        detailsCount: details?.length || 0,
        errorBoundary: allText.includes('Something went wrong'),
        hasConfigPanel: !!root?.querySelector('[class*="space-y-3"]'),
        hasDetailsWithSummary: Array.from(details || []).some(d => !!d.querySelector('summary')),
      };
    });

    console.log('\n=== AFTER CONFIG CLICK ===');
    console.log('Full text:', configState.fullText);
    console.log('Error texts:', configState.errorTexts);
    console.log('Scroll containers:', configState.scrollContainerCount);
    console.log('Failed load:', configState.failedLoad);
    console.log('Details count:', configState.detailsCount);
    console.log('Error boundary:', configState.errorBoundary);
    console.log('Has config panel:', configState.hasConfigPanel);
    console.log('Details with summary:', configState.hasDetailsWithSummary);
  } else {
    console.log('Config button NOT FOUND');
    const btnTexts = [];
    for (const btn of buttons) {
      btnTexts.push(await btn.textContent());
    }
    console.log('Available buttons:', btnTexts);
  }

  console.log('\n=== CONSOLE OUTPUT ===');
  console.log('Errors:', JSON.stringify(errors, null, 2));
  console.log('Warnings (first 5):', JSON.stringify(warnings.slice(0, 5), null, 2));

  await browser.close();
  process.exit(0);
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
