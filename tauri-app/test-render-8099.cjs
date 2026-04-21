const { chromium } = require('playwright');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 300, height: 420 } });
  
  const errors = [];
  page.on('pageerror', err => errors.push(err.message));
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`[BROWSER ${msg.type().toUpperCase()}]`, msg.text());
    }
  });
  
  await page.goto('http://localhost:8099', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);
  
  console.log('\n=== STATUS TAB ===');
  await page.screenshot({ path: '/tmp/status-tab.png', fullPage: true });
  
  const loadingSpinner = await page.$('.animate-spin');
  console.log('Loading spinner present:', !!loadingSpinner);
  
  const textContent = await page.evaluate(() => document.body.textContent);
  console.log('Visible text (first 500):', textContent?.substring(0, 500));
  
  // Click Config tab
  console.log('\n=== CLICKING CONFIG TAB ===');
  const configTab = await page.$('button:has-text("Config")');
  if (configTab) {
    await configTab.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/config-tab.png', fullPage: true });
    
    const configText = await page.evaluate(() => document.body.textContent);
    console.log('Config tab text (first 800):', configText?.substring(0, 800));
    
    const contentInfo = await page.evaluate(() => {
      const flexArea = document.querySelector('.flex-1.overflow-y-auto');
      if (!flexArea) return { error: 'No flex-1 overflow area found' };
      const children = Array.from(flexArea.children).map(c => ({
        tag: c.tagName,
        classes: c.className,
        textLen: (c.textContent || '').length,
        visible: c.offsetHeight > 0,
        height: c.offsetHeight,
        childCount: c.children.length
      }));
      return {
        scrollHeight: flexArea.scrollHeight,
        clientHeight: flexArea.clientHeight,
        overflow: getComputedStyle(flexArea).overflow,
        children
      };
    });
    console.log('Content area:', JSON.stringify(contentInfo, null, 2));
    
    const sections = await page.$$('details');
    console.log('Collapsible sections:', sections.length);
    const labels = await page.$$('label');
    console.log('Labels:', labels.length);
    
  } else {
    console.log('CONFIG TAB NOT FOUND');
  }
  
  console.log('\n=== ERRORS ===');
  errors.forEach(e => console.log('PAGE ERROR:', e));
  if (!errors.length) console.log('No page errors');
  
  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
