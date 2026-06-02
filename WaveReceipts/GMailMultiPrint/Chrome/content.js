// 1. Create a Floating Action Button (FAB)
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

// 2. Monitor for checkbox selections
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

// 3. Handle the Export Process
fab.addEventListener('click', async () => {
    const checkedBoxes = document.querySelectorAll('div[role="checkbox"][aria-checked="true"]');
    const threadIds = [];

    checkedBoxes.forEach(cb => {
        const row = cb.closest('tr') || cb.closest('[role="row"]');
        if (row) {
            let threadId = row.getAttribute('data-legacy-thread-id') || row.getAttribute('data-thread-id');
            if (!threadId) {
                const childWithId = row.querySelector('[data-legacy-thread-id], [data-thread-id]');
                if (childWithId) {
                    threadId = childWithId.getAttribute('data-legacy-thread-id') || childWithId.getAttribute('data-thread-id');
                }
            }
            if (threadId) {
                threadId = threadId.replace('thread-f:', '');
                threadIds.push(threadId);
            }
        }
    });

    if (threadIds.length === 0) {
        alert("Could not detect thread IDs.");
        return;
    }

    fab.innerText = "⏳ Exporting natively... Please wait";
    fab.disabled = true;

    // Process each selected thread one by one
    for (const id of threadIds) {
        await processThread(id);
    }

    fab.innerText = "✅ Done!";
    setTimeout(() => {
        fab.disabled = false;
        document.body.click(); 
    }, 3000);
});

// 4. Scrape Metadata and Trigger Background Print
async function processThread(threadId) {
    const match = window.location.pathname.match(/\/mail\/u\/[0-9]+/);
    const basePath = match ? match[0] : '/mail/u/0';
    const printUrl = `${window.location.origin}${basePath}/?ui=2&ik=&view=pt&search=all&th=${threadId}`;

    try {
        // Fetch the raw HTML temporarily just to scrape the subject and date
        const response = await fetch(printUrl);
        const htmlText = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlText, 'text/html');

        const subjectRaw = doc.querySelector('h2')?.innerText || "Email_Thread";
        const subject = subjectRaw.replace(/[^a-z0-9]/gi, '_').substring(0, 40);

        const dateRaw = doc.querySelector('table tr')?.innerText.match(/\w+ \d+, \d{4}/)?.[0] || new Date().toLocaleDateString();
        const date = dateRaw.replace(/[^a-z0-9]/gi, '_');

        const filename = `${date}_${subject}.pdf`;

        // Tell the background script to open a tab and print it, then await its completion
        await new Promise((resolve) => {
            chrome.runtime.sendMessage({
                action: "printNativePDF",
                printUrl: printUrl,
                filename: filename
            }, (response) => {
                resolve();
            });
        });

    } catch (error) {
        console.error('Failed to process thread:', threadId, error);
    }
}