// 1. Synchronously block Gmail's auto-print BEFORE the page loads
if (window.location.href.includes('ext_print=1')) {
    const script = document.createElement('script');
    script.textContent = 'window.print = function() { console.log("Gmail print suppressed by extension"); };';
    document.documentElement.appendChild(script);
}

// 2. Wrap the UI injection so it waits for the page body to exist
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

    document.addEventListener('click', () => {
        setTimeout(() => {
            const checkedBoxes = document.querySelectorAll('div[role="checkbox"][aria-checked="true"]');
            const selectedCount = checkedBoxes.length;

            if (selectedCount > 0) {
                fab.style.display = 'block';
                fab.innerText = `📄 Native Export ${selectedCount} Threads`;
            } else {
                fab.style.display = 'none';
            }
        }, 200); 
    });

    fab.addEventListener('click', async () => {
        const checkedBoxes = document.querySelectorAll('div[role="checkbox"][aria-checked="true"]');
        const threadIds = [];

        checkedBoxes.forEach(cb => {
            const row = cb.closest('tr') || cb.closest('[role="row"]');
            if (row) {
                let threadId = row.getAttribute('data-legacy-thread-id') || row.getAttribute('data-thread-id');
                if (!threadId) {
                    const childWithId = row.querySelector('[data-legacy-thread-id], [data-thread-id]');
                    if (childWithId) threadId = childWithId.getAttribute('data-legacy-thread-id') || childWithId.getAttribute('data-thread-id');
                }
                if (threadId) threadIds.push(threadId.replace('thread-f:', ''));
            }
        });

        if (threadIds.length === 0) return alert("Could not detect thread IDs.");

        fab.innerText = "⏳ Exporting natively... Please wait";
        fab.disabled = true;

        for (const id of threadIds) {
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

// 3. Process Thread Logic
async function processThread(threadId) {
    const match = window.location.pathname.match(/\/mail\/u\/[0-9]+/);
    const basePath = match ? match[0] : '/mail/u/0';
    
    // We add &ext_print=1 here so our script at the top of the file knows to suppress Gmail
    const printUrl = `${window.location.origin}${basePath}/?ui=2&ik=&view=pt&search=all&th=${threadId}&ext_print=1`;

    try {
        const response = await fetch(printUrl);
        const htmlText = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlText, 'text/html');

        const subjectRaw = doc.querySelector('h2')?.innerText || "Email_Thread";
        const subject = subjectRaw.replace(/[^a-z0-9]/gi, '_').substring(0, 40);

        const dateRaw = doc.querySelector('table tr')?.innerText.match(/\w+ \d+, \d{4}/)?.[0] || new Date().toLocaleDateString();
        const date = dateRaw.replace(/[^a-z0-9]/gi, '_');

        await new Promise((resolve) => {
            browser.runtime.sendMessage({
                action: "printNativePDF",
                printUrl: printUrl,
                filename: `${date}_${subject}.pdf`
            }, () => resolve());
        });

    } catch (error) {
        console.error('Failed to process thread:', threadId, error);
    }
}