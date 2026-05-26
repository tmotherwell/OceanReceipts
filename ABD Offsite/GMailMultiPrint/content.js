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
    display: none; /* Hidden by default */
    transition: background-color 0.2s;
`;
fab.onmouseover = () => fab.style.backgroundColor = '#1557b0';
fab.onmouseout = () => fab.style.backgroundColor = '#1a73e8';
document.body.appendChild(fab);

// 2. Monitor for checkbox selections to show/hide the button
document.addEventListener('click', () => {
    setTimeout(() => {
        // Find all checked boxes in the Gmail UI
        const checkedBoxes = document.querySelectorAll('div[role="checkbox"][aria-checked="true"]');
        const selectedCount = checkedBoxes.length;

        if (selectedCount > 0) {
            fab.style.display = 'block';
            fab.innerText = `📄 Export ${selectedCount} Threads to PDF`;
        } else {
            fab.style.display = 'none';
        }
    }, 200); // Small delay to allow Gmail's UI to update
});

// 3. Handle the Export Process
fab.addEventListener('click', async () => {
    const checkedBoxes = document.querySelectorAll('div[role="checkbox"][aria-checked="true"]');
    const threadIds = [];

    // Aggressive extraction: search for the ID in various DOM structures
    checkedBoxes.forEach(cb => {
        // Look for a standard table row OR a div acting as a row
        const row = cb.closest('tr') || cb.closest('[role="row"]');
        
        if (row) {
            // Strategy A: Check if the ID is on the row itself
            let threadId = row.getAttribute('data-legacy-thread-id') || row.getAttribute('data-thread-id');
            
            // Strategy B: If not on the row, search INSIDE the row for child elements holding the ID
            if (!threadId) {
                const childWithId = row.querySelector('[data-legacy-thread-id], [data-thread-id]');
                if (childWithId) {
                    threadId = childWithId.getAttribute('data-legacy-thread-id') || childWithId.getAttribute('data-thread-id');
                }
            }

            if (threadId) {
                // Strip out any weird prefixes Gmail sometimes adds (like "thread-f:")
                threadId = threadId.replace('thread-f:', '');
                threadIds.push(threadId);
            }
        }
    });

    if (threadIds.length === 0) {
        alert("Could not detect thread IDs. Gmail's layout might be hiding them in this view.");
        return;
    }

    fab.innerText = "⏳ Exporting... Please wait";
    fab.disabled = true;

    // Process each selected thread
    for (const id of threadIds) {
        await downloadThreadAsPDF(id);
    }

    fab.innerText = "✅ Done!";
    setTimeout(() => {
        fab.disabled = false;
        document.body.click(); // Reset the UI check
    }, 3000);
});

// 4. Fetch, Render, and Convert to PDF
async function downloadThreadAsPDF(threadId) {
    const match = window.location.pathname.match(/\/mail\/u\/[0-9]+/);
    const basePath = match ? match[0] : '/mail/u/0';
    const printUrl = `${window.location.origin}${basePath}/?ui=2&ik=&view=pt&search=all&th=${threadId}`;

    try {
        const response = await fetch(printUrl);
        const htmlText = await response.text();

        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlText, 'text/html');

        // 1. Scrape Metadata for the Filename
        // Gmail print view usually puts the subject in an <h2> or title tag
        let subject = doc.querySelector('h2')?.innerText || "Email_Thread";
        // Clean the subject for use as a filename
        subject = subject.replace(/[^a-z0-9]/gi, '_').substring(0, 50);

        // Date is often in a table row or a span with a specific class
        const dateRaw = doc.querySelector('table tr td div:last-child')?.innerText || new Date().toLocaleDateString();
        const dateFormatted = dateRaw.replace(/[^a-z0-9]/gi, '_');

        // 2. Scrubbing
        const dangerousTags = doc.querySelectorAll('script, link[as="script"], link[rel="preload"], link[rel="prefetch"], iframe, object, embed');
        dangerousTags.forEach(tag => tag.remove());

        const iframe = document.createElement('iframe');
        iframe.style.position = 'absolute';
        iframe.style.width = '800px';
        iframe.style.height = '5000px'; 
        iframe.style.left = '-9999px';
        document.body.appendChild(iframe);

        const iframeDoc = iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write('<!DOCTYPE html>' + doc.documentElement.outerHTML);
        iframeDoc.close();

        await new Promise(resolve => setTimeout(resolve, 1500));

        // 3. Set the dynamic filename
        const opt = {
          margin:       0.5,
          filename:     `${dateFormatted}_${subject}.pdf`,
          image:        { type: 'jpeg', quality: 0.98 },
          html2canvas:  { scale: 2, useCORS: true },
          jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        // 4. Save directly
        await html2pdf().set(opt).from(iframeDoc.body).save();

        document.body.removeChild(iframe);
    } catch (error) {
        console.error('Failed to export thread:', threadId, error);
    }
}