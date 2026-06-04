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

// 2. Helper to get unique, visible thread IDs
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

// 3. Monitor for checkbox selections
document.addEventListener('click', () => {
    setTimeout(() => {
        // Use our new helper to get the accurate count
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

// 4. Handle the Export Process
fab.addEventListener('click', async () => {
    const uniqueIds = getUniqueSelectedThreadIds();

    if (uniqueIds.length === 0) {
        alert("Could not detect thread IDs.");
        return;
    }

    fab.innerText = "⏳ Exporting natively... Please wait";
    fab.disabled = true;

    // Process the deduplicated list
    for (const id of uniqueIds) {
        await processThread(id); // (This calls your existing processThread function)
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
        // Clean the subject and limit length so filenames don't get too long
        const subject = subjectRaw.replace(/[^a-z0-9]/gi, '_').substring(0, 60);

        // Extract the full Date and Time to ensure uniqueness 
        // Matches format: "Fri, Apr 10, 2026 at 11:16 PM"
        const fullDateMatch = doc.querySelector('table tr')?.innerText.match(/[a-zA-Z]+, [a-zA-Z]+ \d{1,2}, \d{4} at \d{1,2}:\d{2}\s*[AP]M/i);
        // Fallback to just the date if the time isn't found
        const backupDateMatch = doc.querySelector('table tr')?.innerText.match(/\w+ \d+, \d{4}/);
        
        const dateRaw = fullDateMatch?.[0] || backupDateMatch?.[0] || new Date().toLocaleString();
        const dateFormatted = dateRaw.replace(/[^a-z0-9]/gi, '_');

        // Apply new naming convention: Subject_Date
        const filename = `${subject}_${dateFormatted}.pdf`;

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