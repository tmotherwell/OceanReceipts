// 1. Synchronously block Gmail's auto-print BEFORE the page loads
if (window.location.href.includes('ext_print=1')) {
    const script = document.createElement('script');
    script.textContent = 'window.print = function() { console.log("Gmail print suppressed by extension"); };';
    document.documentElement.appendChild(script);
}

// 2. Helper to get unique, visible thread IDs (Ported from Chrome)
function getUniqueSelectedThreadIds() {
    const selectedElements = document.querySelectorAll(
        'div[role="checkbox"][aria-checked="true"], [role="row"][aria-selected="true"], [role="row"][aria-checked="true"]'
    );
    const threadIds = new Set(); // A Set automatically prevents duplicates

    selectedElements.forEach(node => {
        // Ignore hidden or detached selection markers
        if (node.offsetWidth === 0 || node.offsetHeight === 0) return;

        const row = node.closest('tr, [role="row"]') || node;
        let threadId = row?.getAttribute('data-legacy-thread-id') || row?.getAttribute('data-thread-id');

        if (!threadId) {
            const childWithId = row?.querySelector('[data-legacy-thread-id], [data-thread-id]');
            if (childWithId) {
                threadId = childWithId.getAttribute('data-legacy-thread-id') || childWithId.getAttribute('data-thread-id');
            }
        }

        if (!threadId && node !== row) {
            const directWithId = node.querySelector('[data-legacy-thread-id], [data-thread-id]');
            if (directWithId) {
                threadId = directWithId.getAttribute('data-legacy-thread-id') || directWithId.getAttribute('data-thread-id');
            }
        }

        if (threadId) {
            threadIds.add(threadId.replace(/^thread-f:/, ''));
        }
    });

    return Array.from(threadIds);
}

// 3. Wrap the UI injection so it waits for the page body to exist
const initUI = () => {
    // Prevent the button from showing up on the actual print popup pages
    if (window.location.href.includes('ext_print=1') || window.location.search.includes('view=pt')) {
        return;
    }

    const fab = document.createElement('button');
    fab.style.cssText = `
        position: fixed;
        bottom: 40px;
        right: 40px;
        z-index: 999999;
        padding: 14px 24px;
        background-color: #1a73e8;
        color: white;
        border: none;
        border-radius: 24px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        cursor: pointer;
        font-family: Roboto, Arial, sans-serif;
        font-size: 15px;
        font-weight: 500;
        display: none;
        transition: background-color 0.2s;
    `;
    fab.onmouseover = () => fab.style.backgroundColor = '#1557b0';
    fab.onmouseout = () => fab.style.backgroundColor = '#1a73e8';
    document.body.appendChild(fab);

    // Monitor for checkbox selections using the unique ID helper
    document.addEventListener('click', () => {
        setTimeout(() => {
            const uniqueIds = getUniqueSelectedThreadIds();
            const selectedCount = uniqueIds.length;

            if (selectedCount > 0) {
                fab.style.display = 'block';
                fab.innerText = `📄 Native Export ${selectedCount} Threads`;
            } else {
                fab.style.display = 'none';
            }
        }, 200); 
    });

    // Handle the Export Process
    fab.addEventListener('click', async () => {
        const uniqueIds = getUniqueSelectedThreadIds();

        if (uniqueIds.length === 0) {
            alert("Could not detect thread IDs.");
            return;
        }

        fab.innerText = "⏳ Exporting natively... Please wait";
        fab.disabled = true;

        for (const id of uniqueIds) {
            await processThread(id);
        }

        fab.innerText = "✅ Done!";
        setTimeout(() => {
            fab.disabled = false;
            document.body.click(); 
        }, 3000);
    });
};

// Safe initialization checker
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUI);
} else {
    initUI();
}

// 4. Process Thread Logic
async function processThread(threadId) {
    const match = window.location.pathname.match(/\/mail\/u\/[0-9]+/);
    const basePath = match ? match[0] : '/mail/u/0';
    
    // FIREFOX SPECIFIC: We add &ext_print=1 here so our script at the top of the file knows to suppress Gmail
    const printUrl = `${window.location.origin}${basePath}/?ui=2&ik=&view=pt&search=all&th=${threadId}&ext_print=1`;

    try {
        const response = await fetch(printUrl);
        const htmlText = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlText, 'text/html');

        // PORTED FROM CHROME: Upgraded metadata scraping for dynamic filename
        const subjectRaw = doc.querySelector('h2')?.innerText || "Email_Thread";
        const subject = subjectRaw.replace(/[^a-z0-9]/gi, '_').substring(0, 60);

        const fullDateMatch = doc.querySelector('table tr')?.innerText.match(/[a-zA-Z]+, [a-zA-Z]+ \d{1,2}, \d{4} at \d{1,2}:\d{2}\s*[AP]M/i);
        const backupDateMatch = doc.querySelector('table tr')?.innerText.match(/\w+ \d+, \d{4}/);
        
        const dateRaw = fullDateMatch?.[0] || backupDateMatch?.[0] || new Date().toLocaleString();
        const dateFormatted = dateRaw.replace(/[^a-z0-9]/gi, '_');

        const filename = `${subject}_${dateFormatted}.pdf`;

        await new Promise((resolve) => {
            // FIREFOX SPECIFIC: browser.runtime API
            browser.runtime.sendMessage({
                action: "printNativePDF",
                printUrl: printUrl,
                filename: filename
            }, () => resolve());
        });

    } catch (error) {
        console.error('Failed to process thread:', threadId, error);
    }
}