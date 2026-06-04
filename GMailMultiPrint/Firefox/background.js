browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "printNativePDF") {
        printTabToPDF(request.printUrl, request.filename).then(() => {
            sendResponse({ status: "done" });
        });
        return true; 
    }
});

async function printTabToPDF(url, filename) {
    return new Promise(async (resolve) => {
        try {
            const currentTabs = await browser.tabs.query({ active: true, currentWindow: true });
            const originalTabId = currentTabs[0]?.id;

            const printTab = await browser.tabs.create({ url: url, active: true });
            let isPrinting = false;

            const onUpdatedListener = async (tabId, changeInfo) => {
                if (tabId === printTab.id && changeInfo.status === 'complete') {
                    
                    if (isPrinting) return;
                    isPrinting = true;
                    browser.tabs.onUpdated.removeListener(onUpdatedListener);

                    try {
                        // Trigger the clean, extension-controlled print dialog
                        // Because this runs in an Isolated World, it bypasses the 
                        // suppressor we injected into the main webpage in content.js
                        await browser.scripting.executeScript({
                            target: { tabId: printTab.id },
                            func: () => { window.print(); }
                        });
                    } catch (err) {
                        console.error("Printing operation failed:", err);
                    }

                    // Clean up and return to inbox
                    if (originalTabId) {
                        await browser.tabs.update(originalTabId, { active: true });
                    }
                    browser.tabs.remove(printTab.id);
                    resolve();
                }
            };

            browser.tabs.onUpdated.addListener(onUpdatedListener);

        } catch (globalErr) {
            console.error("Tab handling error:", globalErr);
            resolve();
        }
    });
}