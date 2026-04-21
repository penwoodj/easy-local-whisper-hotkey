const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 300, height: 420 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('http://localhost:8099', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // === STATUS TAB ===
  console.log('\n=== STATUS TAB ===');
  const statusHTML = await page.evaluate(() => {
    const body = document.body;
    return {
      bodyOverflow: getComputedStyle(body).overflow,
      rootOverflow: getComputedStyle(document.getElementById('root')).overflow,
      bodyText: body.innerText.substring(0, 500),
      allText: document.querySelectorAll('*').length,
    };
  });
  console.log('Body overflow:', statusHTML.bodyOverflow);
  console.log('Root overflow:', statusHTML.rootOverflow);
  console.log('Element count:', statusHTML.allText);
  console.log('Body text preview:', statusHTML.bodyText);

  // Check for loading state vs loaded
  const loadingState = await page.evaluate(() => {
    const loading = document.body.textContent.includes('Loading');
    const statusTab = document.body.textContent.includes('Status');
    const modesTab = document.body.textContent.includes('Modes');
    const configTab = document.body.textContent.includes('Config');
    return { loading, statusTab, modesTab, configTab };
  });
  console.log('Loading:', loadingState.loading);
  console.log('Tabs present:', loadingState.statusTab, loadingState.modesTab, loadingState.configTab);

  // Screenshot
  await page.screenshot({ path: '/tmp/pw-live-status.png' });

  // === CONFIG TAB ===
  console.log('\n=== CONFIG TAB ===');
  // Click the Config tab button
  const configTabBtn = await page.$('button:has-text("Config")');
  if (configTabBtn) {
    await configTabBtn.click();
    await page.waitForTimeout(1000);
    
    const configHTML = await page.evaluate(() => {
      const content = document.querySelector('.scroll-container, [class*="scroll"], [class*="overflow"]');
      const allDetails = document.querySelectorAll('details');
      const allLabels = document.querySelectorAll('label');
      const allInputs = document.querySelectorAll('input');
      const allSwitches = document.querySelectorAll('[role="switch"]');
      const allButtons = document.querySelectorAll('button');
      const bodyText = document.body.innerText;
      
      // Check for blank content
      const mainContent = document.querySelector('#root');
      const mainHTML = mainContent ? mainContent.innerHTML.length : 0;
      const mainText = mainContent ? mainContent.textContent.trim().length : 0;
      
      return {
        detailsCount: allDetails.length,
        labelsCount: allLabels.length,
        inputsCount: allInputs.length,
        switchesCount: allSwitches.length,
        buttonsCount: allButtons.length,
        mainHTMLLength: mainHTML,
        mainTextLength: mainText,
        bodyTextPreview: bodyText.substring(0, 1000),
        sectionNames: Array.from(allDetails).map(d => {
          const summary = d.querySelector('summary');
          return summary ? summary.textContent.trim() : '(no summary)';
        }),
        scrollContainerFound: !!content,
      };
    });
    console.log('Details sections:', configHTML.detailsCount);
    console.log('Labels:', configHTML.labelsCount);
    console.log('Inputs:', configHTML.inputsCount);
    console.log('Switches:', configHTML.switchesCount);
    console.log('Buttons:', configHTML.buttonsCount);
    console.log('Main HTML length:', configHTML.mainHTMLLength);
    console.log('Main text length:', configHTML.mainTextLength);
    console.log('Scroll container found:', configHTML.scrollContainerFound);
    console.log('Section names:', configHTML.sectionNames.join(', '));
    console.log('Config body preview:', configHTML.bodyTextPreview);

    // Check if config content is actually visible (not display:none or collapsed)
    const visibilityCheck = await page.evaluate(() => {
      const root = document.getElementById('root');
      const rootStyle = getComputedStyle(root);
      const allVisible = Array.from(root.querySelectorAll('*')).filter(el => {
        const style = getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
      });
      return {
        rootDisplay: rootStyle.display,
        rootVisibility: rootStyle.visibility,
        totalElements: root.querySelectorAll('*').length,
        visibleElements: allVisible.length,
        rootHeight: root.offsetHeight,
        rootScrollHeight: root.scrollHeight,
      };
    });
    console.log('Root display:', visibilityCheck.rootDisplay);
    console.log('Root visibility:', visibilityCheck.rootVisibility);
    console.log('Visible/total elements:', visibilityCheck.visibleElements + '/' + visibilityCheck.totalElements);
    console.log('Root height/scrollHeight:', visibilityCheck.rootHeight + '/' + visibilityCheck.rootScrollHeight);

    await page.screenshot({ path: '/tmp/pw-live-config.png' });
  } else {
    console.log('ERROR: Config tab button not found!');
  }

  // === MODES TAB ===
  console.log('\n=== MODES TAB ===');
  const modesTabBtn = await page.$('button:has-text("Modes")');
  if (modesTabBtn) {
    await modesTabBtn.click();
    await page.waitForTimeout(1000);
    
    const modesHTML = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      const modeButtons = Array.from(buttons).filter(b => {
        const text = b.textContent;
        return text.includes('Off') || text.includes('Light') || text.includes('Aggressive') || 
               text.includes('Agentic') || text.includes('Writing') || text.includes('Code') ||
               text.includes('Structure') || text.includes('Persona') || text.includes('Clarity');
      });
      return {
        modeButtonsFound: modeButtons.length,
        modeButtonDetails: modeButtons.map(b => ({
          text: b.textContent.trim().substring(0, 50),
          classes: b.className,
        })),
      };
    });
    console.log('Mode buttons found:', modesHTML.modeButtonsFound);
    modesHTML.modeButtonDetails.forEach(b => {
      console.log('  Button:', b.text, '| Classes:', b.classes.substring(0, 80));
    });

    await page.screenshot({ path: '/tmp/pw-live-modes.png' });
  } else {
    console.log('ERROR: Modes tab button not found!');
  }

  // === ERRORS ===
  console.log('\n=== CONSOLE ERRORS ===');
  if (errors.length === 0) {
    console.log('No console errors');
  } else {
    errors.forEach(e => console.log('ERROR:', e));
  }

  await browser.close();
})().catch(err => {
  console.error('FATAL:', err.message);
  process.exit(1);
});
