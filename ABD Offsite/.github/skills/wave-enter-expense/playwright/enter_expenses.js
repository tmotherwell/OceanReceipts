const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const yaml = require('js-yaml');
const { chromium } = require('playwright');

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {};
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--config') opts.config = args[++i];
    else if (a === '--input') opts.input = args[++i];
    else if (a === '--headless') opts.headless = true;
    else if (a === '--help') opts.help = true;
  }
  return opts;
}

async function fileExists(p) {
  try {
    await fsp.access(p);
    return true;
  } catch (e) {
    return false;
  }
}

async function loadConfig(configPath) {
  const raw = await fsp.readFile(configPath, 'utf8');
  return yaml.load(raw);
}

function normalize(s = '') {
  return s.replace(/\s+/g, ' ').trim().toLowerCase();
}

async function findReceipt(inputFolder, merchant, date) {
  if (!(await fileExists(inputFolder))) return null;
  const files = await fsp.readdir(inputFolder);
  const target = normalize(`${merchant} - ${date}`);
  const exactMatches = files.filter((fn) => normalize(fn.replace(/\.[^.]+$/, '')) === target);
  if (exactMatches.length > 0) {
    if (exactMatches.length === 1) return path.join(inputFolder, exactMatches[0]);
    let best = exactMatches[0];
    let bestTime = 0;
    for (const f of exactMatches) {
      const stat = await fsp.stat(path.join(inputFolder, f));
      if (stat.mtimeMs > bestTime) {
        bestTime = stat.mtimeMs;
        best = f;
      }
    }
    return path.join(inputFolder, best);
  }
  const fuzzy = files.filter((fn) => {
    const base = normalize(fn.replace(/\.[^.]+$/, ''));
    return base.includes(normalize(merchant)) && base.includes(date);
  });
  if (fuzzy.length === 0) return null;
  let best = fuzzy[0];
  let bestTime = 0;
  for (const f of fuzzy) {
    const stat = await fsp.stat(path.join(inputFolder, f));
    if (stat.mtimeMs > bestTime) {
      bestTime = stat.mtimeMs;
      best = f;
    }
  }
  return path.join(inputFolder, best);
}

async function fillFirst(page, selectors, value) {
  for (const sel of selectors) {
    try {
      const loc = page.locator(sel);
      const cnt = await loc.count();
      if (cnt > 0) {
        await loc.first().fill(value);
        return true;
      }
    } catch (e) {
      // ignore
    }
  }
  return false;
}

async function clickByTextVariants(page, variants) {
  for (const v of variants) {
    try {
      const loc = page.locator(`text=${v}`);
      if ((await loc.count()) > 0) {
        await loc.first().click();
        return true;
      }
    } catch (e) {
      // continue
    }
  }
  return false;
}

async function run() {
  const opts = parseArgs();
  const skillDir = path.resolve(__dirname, '..');
  const configPath = opts.config ? path.resolve(process.cwd(), opts.config) : path.join(skillDir, 'config.local.yaml');
  if (!(await fileExists(configPath))) {
    console.error('Config not found at', configPath);
    process.exit(1);
  }
  const config = await loadConfig(configPath);
  if (!config.email || !config.password_file) {
    console.error('Config missing email or password_file');
    process.exit(1);
  }
  const passwordPath = path.resolve(skillDir, config.password_file);
  if (!(await fileExists(passwordPath))) {
    console.error('Password file missing at', passwordPath);
    process.exit(1);
  }
  const password = (await fsp.readFile(passwordPath, 'utf8')).trim();
  const inputPath = opts.input ? path.resolve(process.cwd(), opts.input) : path.join(skillDir, config.input_folder || 'input', 'expenses.json');
  if (!(await fileExists(inputPath))) {
    console.error('Input JSON missing at', inputPath);
    process.exit(1);
  }
  const raw = await fsp.readFile(inputPath, 'utf8');
  let records;
  try {
    const parsed = JSON.parse(raw);
    records = Array.isArray(parsed) ? parsed : [parsed];
  } catch (e) {
    console.error('Failed parse input JSON', e);
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: !!opts.headless });
  const context = await browser.newContext();
  const page = await context.newPage();
  try {
    await page.goto('https://www.waveapps.com', { waitUntil: 'domcontentloaded' });
    await clickByTextVariants(page, ['Log in', 'Log In', 'Sign in', 'Sign In', 'Log into Wave']);
    await page.waitForTimeout(1000);
    await fillFirst(page, ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="Email"]'], config.email);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1000);
    await fillFirst(page, ['input[type="password"]', 'input[name="password"]', 'input[placeholder*="Password"]'], password);
    await clickByTextVariants(page, ['Sign in', 'Sign In', 'Sign in to Wave']);
    await page.waitForTimeout(4000);

    await clickByTextVariants(page, ['Accounting', 'Accounting & Reports']).catch(() => {});
    await page.waitForTimeout(500);
    await clickByTextVariants(page, ['Transactions']).catch(() => {});
    await page.waitForTimeout(2000);

    const inputFolder = path.join(skillDir, config.input_folder || 'input');
    for (const rec of records) {
      console.log('Processing', rec);
      await clickByTextVariants(page, ['Add transaction', 'Add Transaction', '+ Add transaction', 'Add']).catch(() => {});
      await page.waitForTimeout(500);
      await clickByTextVariants(page, ['Add withdrawal', 'Add Withdrawal']).catch(() => {});
      await page.waitForTimeout(800);

      await fillFirst(page, ['input[type="date"]', 'input[placeholder*="Date"]', 'input[aria-label*="Date"]', 'input[name="date"]'], rec.date);
      await fillFirst(page, ['input[placeholder*="Description"]', 'input[aria-label*="Description"]', 'input[name="description"]', 'textarea[name="description"]'], rec.merchant);

      // Select account to Shareholder Loan
      let done = false;
      const selDropdown = ['select[name="account"]', 'select[aria-label*="Account"]'];
      for (const sel of selDropdown) {
        try {
          const cnt = await page.locator(sel).count();
          if (cnt > 0) {
            await page.locator(sel).first().selectOption({ label: 'Shareholder Loan' }).catch(() => {});
            done = true;
            break;
          }
        } catch (e) {}
      }
      if (!done) {
        await clickByTextVariants(page, ['Account']).catch(() => {});
        await page.waitForTimeout(300);
        await clickByTextVariants(page, ['Shareholder Loan']).catch(() => {});
      }

      await fillFirst(page, ['input[placeholder*="Amount"]', 'input[aria-label*="Amount"]', 'input[name="amount"]', 'input[type="number"]'], String(rec.total));

      const receiptPath = await findReceipt(inputFolder, rec.merchant, rec.date);
      if (receiptPath) {
        const fileInputSelectors = ['input[type="file"]', 'input[accept]'];
        let attached = false;
        for (const s of fileInputSelectors) {
          try {
            const count = await page.locator(s).count();
            if (count > 0) {
              await page.locator(s).first().setInputFiles(receiptPath);
              attached = true;
              break;
            }
          } catch (e) {}
        }
        if (!attached) {
          console.warn('Could not attach file via input selector; receipt found at', receiptPath);
        }
      } else {
        console.warn('No receipt found for', rec.merchant, rec.date);
      }

      await page.waitForTimeout(5000);
      await clickByTextVariants(page, ['Save', 'Save Transaction', 'Save changes']).catch(() => {});
      await page.waitForTimeout(1500);
    }
  } catch (err) {
    console.error('Automation failed', err);
  } finally {
    await browser.close();
  }
}

run();
