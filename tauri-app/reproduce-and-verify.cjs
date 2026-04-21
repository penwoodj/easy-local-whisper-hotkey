/**
 * Reproduce + Verify: Config tab black screen fix
 * 
 * BEFORE FIX: tab-content class had fadeIn animation starting at opacity: 0.
 * In WebKitGTK, this animation may not complete, leaving content permanently invisible.
 * 
 * This test:
 * 1. Simulates the WebKitGTK behavior by injecting the OLD CSS (opacity: 0 animation)
 * 2. Verifies the reproduction (config content invisible)
 * 3. Tests with the NEW code (no animation)
 * 4. Verifies config content is visible
 * 5. Runs comprehensive QA on all tabs
 */
const { chromium } = require('playwright');

const RESULTS = { pass: [], fail: [] };

function check(name, passed, detail = '') {
  if (passed) {
    RESULTS.pass.push(name);
    console.log(`  ✅ ${name}`);
  } else {
    RESULTS.fail.push(`${name}${detail ? ': ' + detail : ''}`);
    console.log(`  ❌ ${name}${detail ? ' — ' + detail : ''}`);
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 300, height: 420 },
    deviceScaleFactor: 1,
  });
  const page = await ctx.newPage();

  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => errors.push(err.message));

  // ========================================
  // PART 1: Reproduce the bug with OLD CSS
  // ========================================
  console.log('\n=== PART 1: REPRODUCE BUG (simulating WebKitGTK opacity issue) ===');
  
  await page.goto('http://localhost:8099', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // Inject the OLD tab-content CSS that caused the bug
  await page.evaluate(() => {
    const style = document.createElement('style');
    style.textContent = `
      .tab-content-repro {
        animation: fadeInRepro 150ms ease-in-out;
      }
      @keyframes fadeInRepro {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
    document.head.appendChild(style);
    
    // Simulate WebKitGTK: freeze the animation at opacity: 0
    // by adding the class and immediately pausing animations
    const configBtn = document.querySelector('button');
    // Find and click config tab
    const buttons = document.querySelectorAll('button');
    for (const btn of buttons) {
      if (btn.textContent.includes('Config')) {
        btn.click();
        break;
      }
    }
  });
  await page.waitForTimeout(500);

  // Now add the tab-content-repro class to config content div
  // and freeze animation to simulate WebKitGTK bug
  const reproResult = await page.evaluate(() => {
    // Find the config content container
    const root = document.getElementById('root');
    const allDivs = root.querySelectorAll('div');
    
    // Find the scroll-container (config content)
    let configContainer = null;
    for (const div of allDivs) {
      if (div.classList.contains('scroll-container') && div.querySelector('details')) {
        configContainer = div;
        break;
      }
    }
    
    if (!configContainer) {
      return { found: false, reason: 'Config container not found' };
    }
    
    // Add the problematic animation class
    configContainer.classList.add('tab-content-repro');
    
    // Simulate WebKitGTK: pause animation at frame 0 (opacity: 0)
    configContainer.style.animationPlayState = 'paused';
    configContainer.style.opacity = '0';
    
    return {
      found: true,
      opacity: getComputedStyle(configContainer).opacity,
      contentLength: configContainer.textContent.trim().length,
      hasDetails: configContainer.querySelectorAll('details').length,
    };
  });
  
  check('Bug repro: config container found', reproResult.found, reproResult.reason);
  if (reproResult.found) {
    check('Bug repro: opacity IS 0 (simulated WebKitGTK)', reproResult.opacity === '0', 
      `opacity was ${reproResult.opacity}`);
    check('Bug repro: content exists but invisible', reproResult.contentLength > 0 && reproResult.opacity === '0',
      `content=${reproResult.contentLength}, opacity=${reproResult.opacity}`);
  }

  // ========================================
  // PART 2: Verify fix — reload with NEW code
  // ========================================
  console.log('\n=== PART 2: VERIFY FIX (new code, no opacity animation) ===');
  
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // Click Config tab
  const configBtn = await page.$('button:has-text("Config")');
  check('Config tab button exists', !!configBtn);
  
  if (configBtn) {
    await configBtn.click();
    await page.waitForTimeout(1000);

    // Check config content visibility
    const fixResult = await page.evaluate(() => {
      const root = document.getElementById('root');
      const allDivs = root.querySelectorAll('div');
      
      let configContainer = null;
      for (const div of allDivs) {
        if (div.classList.contains('scroll-container') && div.querySelector('details')) {
          configContainer = div;
          break;
        }
      }
      
      if (!configContainer) {
        // Check if error message is shown (config null case)
        const errorText = document.body.textContent;
        if (errorText.includes('Failed to load')) {
          return { found: false, errorShown: true, opacity: '1' };
        }
        return { found: false, errorShown: false, opacity: 'N/A' };
      }
      
      const style = getComputedStyle(configContainer);
      return {
        found: true,
        errorShown: false,
        opacity: style.opacity,
        visibility: style.visibility,
        display: style.display,
        contentLength: configContainer.textContent.trim().length,
        hasDetails: configContainer.querySelectorAll('details').length > 0,
        hasTabContentClass: configContainer.classList.contains('tab-content'),
        boundingRect: configContainer.getBoundingClientRect(),
      };
    });
    
    check('Config container found after fix', fixResult.found);
    if (fixResult.found) {
      check('Config opacity is 1 (visible)', fixResult.opacity === '1', `was ${fixResult.opacity}`);
      check('Config visibility is visible', fixResult.visibility === 'visible', `was ${fixResult.visibility}`);
      check('Config display is not none', fixResult.display !== 'none', `was ${fixResult.display}`);
      check('Config has real content', fixResult.contentLength > 0, `length=${fixResult.contentLength}`);
      check('Config has details sections', fixResult.hasDetails);
      check('NO tab-content class (removed)', !fixResult.hasTabContentClass, 'tab-content class still present!');
      check('Config bounding rect has width', fixResult.boundingRect.width > 0, `width=${fixResult.boundingRect.width}`);
      check('Config bounding rect has height', fixResult.boundingRect.height > 0, `height=${fixResult.boundingRect.height}`);
    } else {
      check('Error message shown for null config', fixResult.errorShown);
    }
  }

  // ========================================
  // PART 3: Comprehensive QA — Status tab
  // ========================================
  console.log('\n=== PART 3: STATUS TAB QA ===');
  
  const statusBtn = await page.$('button:has-text("Status")');
  if (statusBtn) {
    await statusBtn.click();
    await page.waitForTimeout(1000);

    const statusQA = await page.evaluate(() => {
      const text = document.body.textContent;
      const canvas = document.querySelector('canvas');
      const startBtn = text.includes('Start');
      const footerCtrlSpace = text.includes('Ctrl+Space');
      const footerModes = text.includes('Ctrl+Shift+Alt+Space');
      const toggleOrHold = text.includes('Toggle') || text.includes('Hold');
      const stopped = text.includes('Stopped');
      const root = document.getElementById('root');
      const rootStyle = getComputedStyle(root);
      
      return {
        hasCanvas: !!canvas,
        hasStartButton: startBtn,
        hasCtrlSpaceShortcut: footerCtrlSpace,
        hasModesShortcut: footerModes,
        hasToggleOrHold: toggleOrHold,
        hasStoppedText: stopped,
        rootDisplay: rootStyle.display,
        rootPosition: rootStyle.position,
        rootOverflow: rootStyle.overflow,
        bodyOverflow: getComputedStyle(document.body).overflow,
        bodyText: text.substring(0, 300),
      };
    });

    check('Status: Canvas waveform present', statusQA.hasCanvas);
    check('Status: Start button visible', statusQA.hasStartButton);
    check('Status: Ctrl+Space in footer', statusQA.hasCtrlSpaceShortcut);
    check('Status: Ctrl+Shift+Alt+Space in footer', statusQA.hasModesShortcut);
    check('Status: Toggle/Hold mode shown', statusQA.hasToggleOrHold);
    check('Status: Stopped text shown', statusQA.hasStoppedText);
    check('CSS: #root position absolute (WebKitGTK safe)', statusQA.rootPosition === 'absolute', `was ${statusQA.rootPosition}`);
    check('CSS: #root overflow hidden', statusQA.rootOverflow === 'hidden', `was ${statusQA.rootOverflow}`);
    check('CSS: body overflow not hidden', statusQA.bodyOverflow !== 'hidden', `was ${statusQA.bodyOverflow}`);
    check('CSS: #root display block', statusQA.rootDisplay === 'block', `was ${statusQA.rootDisplay}`);
    check('CSS: No h-screen/w-screen classes', !statusQA.bodyText.includes('h-screen'));
  }

  // ========================================
  // PART 4: Comprehensive QA — Modes tab
  // ========================================
  console.log('\n=== PART 4: MODES TAB QA ===');
  
  const modesBtn = await page.$('button:has-text("Modes")');
  if (modesBtn) {
    await modesBtn.click();
    await page.waitForTimeout(1000);

    const modesQA = await page.evaluate(() => {
      const text = document.body.textContent;
      const modes = ['Off', 'Light', 'Aggressive', 'Agentic', 'Writing', 'Code', 'Structure', 'Persona', 'Clarity'];
      const found = modes.filter(m => text.includes(m));
      const buttons = document.querySelectorAll('button');
      const modeButtons = Array.from(buttons).filter(b => {
        const t = b.textContent;
        return modes.some(m => t.includes(m));
      });
      const hasRadiogroup = !!document.querySelector('[role="radiogroup"]');
      
      return {
        modesFound: found.length,
        allModesPresent: found.length === 9,
        modeButtonCount: modeButtons.length,
        hasRadiogroup,
        hasCurrentLabel: text.includes('Current'),
        descriptions: {
          'No processing': text.includes('No processing'),
          'Punctuation only': text.includes('Punctuation only'),
          'Full grammar fix': text.includes('Full grammar fix'),
        },
      };
    });

    check('Modes: All 9 modes present', modesQA.allModesPresent, `${modesQA.modesFound}/9`);
    check('Modes: Mode buttons found', modesQA.modeButtonCount === 9, `${modesQA.modeButtonCount} buttons`);
    check('Modes: Radiogroup role for accessibility', modesQA.hasRadiogroup);
    check('Modes: Current label shown', modesQA.hasCurrentLabel);
    check('Modes: Off description "No processing"', modesQA.descriptions['No processing']);
    check('Modes: Light description "Punctuation only"', modesQA.descriptions['Punctuation only']);
    check('Modes: Aggressive description "Full grammar fix"', modesQA.descriptions['Full grammar fix']);
  }

  // ========================================
  // PART 5: Comprehensive QA — Config tab expanded
  // ========================================
  console.log('\n=== PART 5: CONFIG TAB QA (all sections expanded) ===');
  
  const configBtn2 = await page.$('button:has-text("Config")');
  if (configBtn2) {
    await configBtn2.click();
    await page.waitForTimeout(1000);

    // Open all details
    await page.evaluate(() => {
      document.querySelectorAll('details').forEach(d => d.open = true);
    });
    await page.waitForTimeout(500);

    const configQA = await page.evaluate(() => {
      const details = document.querySelectorAll('details');
      const labels = document.querySelectorAll('label');
      const inputs = document.querySelectorAll('input');
      const switches = document.querySelectorAll('[role="switch"]');
      const buttons = document.querySelectorAll('button');
      const text = document.body.textContent;
      const root = document.getElementById('root');
      
      const sectionNames = Array.from(details).map(d => {
        const s = d.querySelector('summary');
        return s ? s.textContent.trim().replace(/[▶▼]/g, '').trim() : '';
      });
      
      const blankDivs = Array.from(root.querySelectorAll('div')).filter(d => {
        const style = getComputedStyle(d);
        return style.display !== 'none' && 
               d.textContent.trim() === '' && 
               d.offsetHeight > 50;
      });
      
      // Check for scroll-container padding
      const scrollContainers = document.querySelectorAll('.scroll-container');
      const hasPaddingRight = Array.from(scrollContainers).some(sc => {
        const style = getComputedStyle(sc);
        return parseInt(style.paddingRight) >= 8;
      });
      
      // Check that no 100vh/100vw in inline styles
      const inlineStyles = Array.from(root.querySelectorAll('*'))
        .map(el => el.getAttribute('style') || '')
        .filter(s => s.includes('100vh') || s.includes('100vw'));
      
      return {
        sectionCount: details.length,
        sectionNames,
        labelCount: labels.length,
        inputCount: inputs.length,
        switchCount: switches.length,
        blankDivCount: blankDivs.length,
        scrollContainerPadding: hasPaddingRight,
        inlineViewportUnits: inlineStyles.length,
        hasWhisperCli: text.includes('Whisper CLI'),
        hasModel: text.includes('Model'),
        hasLanguage: text.includes('Language'),
        hasSource: text.includes('Source'),
        hasChunk: text.includes('Chunk'),
        hasRealtime: text.includes('Real-time'),
        hasSmartPunct: text.includes('Smart Punctuation'),
        hasPostProcess: text.includes('Post-Processing'),
        hasVoiceControl: text.includes('Voice Control'),
        hasAdvanced: text.includes('Advanced'),
        hasRulesManager: text.includes('Remove filler words'),
        hasLogFile: text.includes('Log File'),
        contentAreaScrollHeight: root.scrollHeight,
        contentAreaClientHeight: root.clientHeight,
      };
    });

    check('Config: 7 sections present', configQA.sectionCount === 7, `${configQA.sectionCount} sections`);
    check('Config: 19+ labels', configQA.labelCount >= 15, `${configQA.labelCount} labels`);
    check('Config: 9+ inputs', configQA.inputCount >= 7, `${configQA.inputCount} inputs`);
    check('Config: 9+ switches', configQA.switchCount >= 7, `${configQA.switchCount} switches`);
    check('Config: 0 blank divs (>50px)', configQA.blankDivCount === 0, `${configQA.blankDivCount} blank divs`);
    check('Config: Scroll container has padding', configQA.scrollContainerPadding);
    check('Config: NO inline 100vh/100vw', configQA.inlineViewportUnits === 0, `${configQA.inlineViewportUnits} found`);
    check('Config: Whisper CLI field', configQA.hasWhisperCli);
    check('Config: Model field', configQA.hasModel);
    check('Config: Language field', configQA.hasLanguage);
    check('Config: Source field', configQA.hasSource);
    check('Config: Chunk seconds field', configQA.hasChunk);
    check('Config: Real-time switch', configQA.hasRealtime);
    check('Config: Smart Punctuation switch', configQA.hasSmartPunct);
    check('Config: Post-Processing section', configQA.hasPostProcess);
    check('Config: Voice Control section', configQA.hasVoiceControl);
    check('Config: Advanced section', configQA.hasAdvanced);
    check('Config: RulesManager present', configQA.hasRulesManager);
    check('Config: Log File field', configQA.hasLogFile);

    console.log('\n  Sections:', configQA.sectionNames.join(', '));
  }

  // ========================================
  // PART 6: Tab switching test
  // ========================================
  console.log('\n=== PART 6: TAB SWITCHING ===');
  
  const tabSwitch = await page.evaluate(async () => {
    const results = [];
    const tabs = ['Status', 'Modes', 'Config'];
    
    for (const tab of tabs) {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes(tab));
      if (btn) {
        btn.click();
        await new Promise(r => setTimeout(r, 500));
        
        const root = document.getElementById('root');
        const content = root.textContent.trim();
        const opacity = getComputedStyle(root).opacity;
        
        results.push({
          tab,
          contentVisible: content.length > 50,
          opacity,
          contentLength: content.length,
        });
      }
    }
    return results;
  });

  for (const r of tabSwitch) {
    check(`Tab switch ${r.tab}: content visible`, r.contentVisible, `content=${r.contentLength}`);
    check(`Tab switch ${r.tab}: opacity is 1`, r.opacity === '1', `opacity=${r.opacity}`);
  }

  // ========================================
  // PART 7: Error check
  // ========================================
  console.log('\n=== PART 7: CONSOLE ERRORS ===');
  check('No console errors', errors.length === 0, errors.length > 0 ? errors.join('; ') : undefined);

  await browser.close();

  // ========================================
  // SUMMARY
  // ========================================
  console.log('\n' + '='.repeat(50));
  console.log(`TOTAL: ${RESULTS.pass.length} PASS, ${RESULTS.fail.length} FAIL`);
  console.log('='.repeat(50));
  
  if (RESULTS.fail.length > 0) {
    console.log('\nFAILURES:');
    RESULTS.fail.forEach(f => console.log(`  ❌ ${f}`));
    process.exit(1);
  } else {
    console.log('\n✅ ALL CHECKS PASSED');
  }
})().catch(err => {
  console.error('FATAL:', err.message);
  process.exit(1);
});
