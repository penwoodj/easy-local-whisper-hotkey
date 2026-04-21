const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const DIST = path.join(__dirname, 'dist');
const PORT = 8101;
const BASE = `http://localhost:${PORT}`;

function serve() {
  return new Promise((resolve) => {
    const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml' };
    const s = http.createServer((req, res) => {
      let fp = path.join(DIST, req.url === '/' ? 'index.html' : req.url);
      const ext = path.extname(fp);
      fs.readFile(fp, (err, data) => {
        if (err) { res.writeHead(404); res.end(); return; }
        res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
        res.end(data);
      });
    });
    s.listen(PORT, () => resolve(s));
  });
}

async function run() {
  const server = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 300, height: 480 } });
  
  const issues = [];
  const passes = [];

  function pass(msg) { passes.push(`  ✅ ${msg}`); }
  function fail(msg) { issues.push(`  ❌ ${msg}`); }

  // Collect console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => consoleErrors.push(`PAGE ERROR: ${err.message}`));

  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(500);

  console.log('\n=== WINDOW METRICS ===');
  const winSize = page.viewportSize();
  console.log(`Viewport: ${winSize.width}x${winSize.height}`);

  // Check body/root styles
  const bodyStyles = await page.evaluate(() => {
    const body = document.body;
    const root = document.getElementById('root');
    return {
      bodyOverflow: getComputedStyle(body).overflow,
      bodyMargin: getComputedStyle(body).margin,
      rootOverflow: root ? getComputedStyle(root).overflow : 'N/A',
      rootHeight: root ? root.scrollHeight : 0,
      bodyHeight: body.scrollHeight,
    };
  });
  console.log(`body overflow: ${bodyStyles.bodyOverflow}, margin: ${bodyStyles.bodyMargin}`);
  console.log(`#root overflow: ${bodyStyles.rootOverflow}, scrollHeight: ${bodyStyles.rootHeight}`);
  
  if (bodyStyles.bodyOverflow === 'hidden') fail('body has overflow:hidden — blocks ALL scrolling');
  else pass('body overflow is NOT hidden');
  
  if (bodyStyles.rootOverflow === 'hidden') pass('#root has overflow:hidden (correct — scroll in inner containers)');
  else fail('#root overflow should be hidden');

  // ========== STATUS TAB ==========
  console.log('\n=== STATUS TAB ===');
  await page.screenshot({ path: '/tmp/pw-status.png' });
  
  const statusContent = await page.evaluate(() => {
    const tab = document.querySelector('[data-testid="status-tab"]') || document.querySelector('button');
    const allText = document.body.innerText;
    const buttons = [...document.querySelectorAll('button')].map(b => ({
      text: b.textContent?.trim(),
      disabled: b.disabled,
      classes: b.className,
    }));
    const cards = [...document.querySelectorAll('[class*="card"]')].map(c => ({
      text: c.textContent?.trim().substring(0, 100),
      classes: c.className,
    }));
    const footers = [...document.querySelectorAll('footer, [class*="footer"]')].map(f => f.textContent?.trim());
    
    // Check for volume waveform
    const canvas = document.querySelector('canvas');
    
    return { allText: allText.substring(0, 2000), buttons, cards, footers, hasCanvas: !!canvas };
  });
  console.log('Page text (first 500):', statusContent.allText.substring(0, 500));
  console.log(`Canvas (waveform): ${statusContent.hasCanvas ? 'FOUND' : 'MISSING'}`);
  if (!statusContent.hasCanvas) fail('Volume waveform canvas missing from Status tab');
  else pass('Volume waveform canvas present');

  // Check Start button
  const startBtn = statusContent.buttons.find(b => b.text?.includes('Start'));
  if (startBtn) { pass(`Start button found: "${startBtn.text}"`); }
  else { fail('Start button not found on Status tab'); }

  // Check footer shortcuts
  if (statusContent.allText.includes('Ctrl+Space') && statusContent.allText.includes('Ctrl+Shift+Alt+Space')) {
    pass('Footer keyboard shortcuts present');
  } else {
    fail('Footer keyboard shortcuts missing or incorrect');
    console.log('Footer content:', statusContent.footers);
  }

  // ========== CONFIG TAB ==========
  console.log('\n=== CONFIG TAB ===');
  
  // Click config tab
  const configTabClicked = await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const configBtn = btns.find(b => b.textContent?.includes('Config'));
    if (configBtn) { configBtn.click(); return true; }
    return false;
  });
  await page.waitForTimeout(300);
  
  if (!configTabClicked) { fail('Config tab button not found'); }
  else { pass('Config tab clicked'); }
  
  await page.screenshot({ path: '/tmp/pw-config.png' });

  const configContent = await page.evaluate(() => {
    const allText = document.body.innerText;
    
    // Check for collapsible sections (details/summary)
    const details = [...document.querySelectorAll('details')];
    const sections = details.map(d => ({
      summary: d.querySelector('summary')?.textContent?.trim(),
      open: d.hasAttribute('open'),
      childCount: d.querySelectorAll('input, select, button, [role="switch"], [role="combobox"]').length,
      textPreview: d.textContent?.trim().substring(0, 200),
    }));
    
    // Check for inputs
    const inputs = [...document.querySelectorAll('input')];
    const inputInfo = inputs.map(i => ({
      type: i.type,
      value: i.value?.substring(0, 50),
      placeholder: i.placeholder,
      disabled: i.disabled,
      id: i.id,
      labelText: i.labels?.[0]?.textContent || document.querySelector(`label[for="${i.id}"]`)?.textContent,
    }));
    
    // Check for switches
    const switches = [...document.querySelectorAll('[role="switch"]')];
    const switchInfo = switches.map(s => ({
      ariaLabel: s.getAttribute('aria-label'),
      checked: s.getAttribute('aria-checked'),
      disabled: s.hasAttribute('disabled') || s.getAttribute('data-disabled') === 'true',
    }));
    
    // Check for comboboxes (audio source, language selects)
    const comboboxes = [...document.querySelectorAll('[role="combobox"]')];
    const comboInfo = comboboxes.map(c => ({
      text: c.textContent?.trim().substring(0, 50),
      disabled: c.disabled || c.getAttribute('aria-disabled') === 'true',
    }));
    
    // Check if config content area is blank
    const configArea = document.querySelector('[data-testid="config-content"]') || 
                       document.querySelector('[class*="config"]') ||
                       document.querySelector('main') || document.getElementById('root');
    
    // Check scrollability  
    const scrollContainers = [...document.querySelectorAll('*')].filter(el => {
      const s = getComputedStyle(el);
      return (s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight;
    }).map(el => ({
      tag: el.tagName,
      class: el.className?.substring(0, 60),
      scrollH: el.scrollHeight,
      clientH: el.clientHeight,
      canScroll: el.scrollHeight > el.clientHeight,
    }));
    
    return {
      allTextLength: allText.length,
      allText: allText.substring(0, 3000),
      sections,
      inputCount: inputs.length,
      inputInfo: inputInfo.slice(0, 10),
      switchCount: switches.length,
      switchInfo,
      comboboxCount: comboboxes.length,
      comboInfo,
      scrollContainers: scrollContainers.slice(0, 5),
      configAreaText: configArea?.textContent?.trim().substring(0, 200) || 'NOT FOUND',
    };
  });
  
  console.log(`Config text length: ${configContent.allTextLength}`);
  console.log(`Sections found: ${configContent.sections.length}`);
  configContent.sections.forEach(s => {
    console.log(`  Section: "${s.summary}" open=${s.open} children=${s.childCount}`);
  });
  console.log(`Inputs: ${configContent.inputCount}`);
  console.log(`Switches: ${configContent.switchCount}`);
  console.log(`Comboboxes: ${configContent.comboboxCount}`);
  
  if (configContent.sections.length >= 6) pass(`Found ${configContent.sections.length} collapsible sections`);
  else fail(`Only ${configContent.sections.length} sections (expected 7)`);
  
  if (configContent.inputCount >= 5) pass(`Found ${configContent.inputCount} input fields`);
  else fail(`Only ${configContent.inputCount} inputs — config may be blank`);
  
  if (configContent.switchCount >= 5) pass(`Found ${configContent.switchCount} switches`);
  else fail(`Only ${configContent.switchCount} switches — missing feature toggles`);

  // Check specific sections exist
  const requiredSections = ['Audio', 'Source', 'Streaming', 'Feature', 'Post-Process', 'Voice', 'Advanced'];
  const sectionText = configContent.sections.map(s => s.summary).join(' ');
  requiredSections.forEach(req => {
    if (sectionText.match(new RegExp(req, 'i'))) pass(`Section "${req}" present`);
    else fail(`Section "${req}" MISSING from Config tab`);
  });

  // ========== MODES TAB ==========
  console.log('\n=== MODES TAB ===');
  const modesTabClicked = await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const modesBtn = btns.find(b => b.textContent?.includes('Mode'));
    if (modesBtn) { modesBtn.click(); return true; }
    return false;
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/tmp/pw-modes.png' });

  const modesContent = await page.evaluate(() => {
    const allText = document.body.innerText;
    const modeButtons = [...document.querySelectorAll('button')].filter(b => 
      ['Off','Light','Aggressive','Agentic','Writing','Code','Structure','Persona','Clarity']
        .some(m => b.textContent?.trim() === m)
    );
    return {
      modeButtons: modeButtons.length,
      modeNames: modeButtons.map(b => b.textContent?.trim()),
      hasActiveStyle: modeButtons.some(b => b.className.includes('border-primary') || b.className.includes('ring')),
      allText: allText.substring(0, 500),
    };
  });
  
  console.log(`Mode buttons: ${modesContent.modeButtons}`);
  console.log(`Modes: ${modesContent.modeNames.join(', ')}`);
  
  if (modesContent.modeButtons === 9) pass('All 9 mode buttons present');
  else fail(`Only ${modesContent.modeButtons}/9 mode buttons`);
  
  if (modesContent.hasActiveStyle) pass('Active mode has border/ring styling');
  else fail('No active mode styling detected');

  // ========== CHECK FOR CSS/DISPLAY ISSUES ==========
  console.log('\n=== CSS & LAYOUT CHECKS ===');
  
  const cssChecks = await page.evaluate(() => {
    const checks = [];
    
    // Check all buttons for proper sizing
    const allButtons = [...document.querySelectorAll('button')];
    const wideButtons = allButtons.filter(b => {
      const rect = b.getBoundingClientRect();
      return rect.width > 260; // wider than 260px in 300px viewport is too wide
    }).map(b => ({
      text: b.textContent?.trim().substring(0, 30),
      width: Math.round(b.getBoundingClientRect().width),
    }));
    if (wideButtons.length > 0) checks.push({ issue: 'OVERLY_WIDE_BUTTONS', buttons: wideButtons });
    
    // Check for elements outside viewport
    const outsideViewport = [...document.querySelectorAll('*')].filter(el => {
      const rect = el.getBoundingClientRect();
      return rect.right > 310 || rect.left < -10;
    }).length;
    checks.push({ label: 'elements_outside_viewport', count: outsideViewport });
    
    // Check padding on scrollable areas
    const scrollables = [...document.querySelectorAll('*')].filter(el => {
      const s = getComputedStyle(el);
      return (s.overflowY === 'auto' || s.overflowY === 'scroll');
    }).map(el => {
      const s = getComputedStyle(el);
      return {
        paddingRight: s.paddingRight,
        hasScroll: el.scrollHeight > el.clientHeight,
        scrollDiff: el.scrollHeight - el.clientHeight,
      };
    });
    checks.push({ label: 'scrollable_areas', data: scrollables.slice(0, 5) });
    
    // Check for blank/empty visible areas
    const blankAreas = [...document.querySelectorAll('div')].filter(el => {
      const rect = el.getBoundingClientRect();
      const text = el.textContent?.trim();
      return rect.height > 50 && rect.width > 50 && (!text || text.length === 0) && 
             rect.top > 0 && rect.top < 480;
    }).length;
    checks.push({ label: 'large_blank_divs', count: blankAreas });
    
    return checks;
  });
  
  cssChecks.forEach(c => {
    if (c.issue === 'OVERLY_WIDE_BUTTONS') {
      fail(`Overly wide buttons (>260px in 300px viewport): ${JSON.stringify(c.buttons)}`);
    } else if (c.label === 'elements_outside_viewport' && c.count > 5) {
      fail(`${c.count} elements outside viewport`);
    } else if (c.label === 'elements_outside_viewport') {
      pass(`Only ${c.count} elements outside viewport (tolerable)`);
    } else if (c.label === 'large_blank_divs' && c.count > 3) {
      fail(`${c.count} large blank divs found (layout issue)`);
    } else if (c.label === 'large_blank_divs') {
      pass(`Only ${c.count} large blank divs`);
    } else if (c.label === 'scrollable_areas') {
      c.data.forEach(s => {
        if (s.hasScroll && parseInt(s.paddingRight) < 8) {
          fail(`Scrollable area with padding-right ${s.paddingRight} (need >=8px)`);
        }
      });
      if (!c.data.some(s => s.hasScroll && parseInt(s.paddingRight) < 8)) {
        pass('Scrollable areas have adequate padding');
      }
    }
  });

  // ========== CONSOLE ERRORS ==========
  console.log('\n=== CONSOLE ERRORS ===');
  if (consoleErrors.length === 0) {
    pass('No console errors');
  } else {
    consoleErrors.forEach(e => {
      fail(`Console error: ${e.substring(0, 120)}`);
    });
  }

  // ========== FINAL SUMMARY ==========
  console.log('\n' + '='.repeat(60));
  console.log('ISSUES FOUND:');
  if (issues.length === 0) console.log('  None!');
  else issues.forEach(i => console.log(i));
  
  console.log('\nPASSES:');
  passes.forEach(p => console.log(p));
  
  console.log(`\nTotal: ${passes.length} passes, ${issues.length} issues`);

  await browser.close();
  server.close();
  
  process.exit(issues.length > 0 ? 1 : 0);
}

run().catch(e => { console.error('FATAL:', e); process.exit(2); });
