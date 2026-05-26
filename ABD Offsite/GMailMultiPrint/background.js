chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "printNativePDF") {
        // Execute the async function and tell Chrome to wait for the response
        printTabToPDF(request.printUrl, request.filename).then(() => {
            sendResponse({ status: "done" });
        });
        return true; // Keeps the message channel open
    }
});

async function printTabToPDF(url, filename) {
    return new Promise(async (resolve) => {
        // 1. Create a new tab in the background
        const tab = await chrome.tabs.create({ url: url, active: false });

        // 2. Attach the Chrome Debugger to the new tab
        chrome.debugger.attach({ tabId: tab.id }, "1.3", () => {
            
            // 3. Give Gmail 2 seconds to load its CSS and images
            setTimeout(() => {
                
                // 4. Send the DevTools command to generate a native PDF
                chrome.debugger.sendCommand(
                    { tabId: tab.id },
                    "Page.printToPDF",
                    {
                        landscape: false,
                        displayHeaderFooter: false,
                        printBackground: true
                    },
                    (result) => {
                        // 5. Download the raw PDF data
                        if (result && result.data) {
                            chrome.downloads.download({
                                url: "data:application/pdf;base64," + result.data,
                                filename: filename,
                                saveAs: false
                            });
                        }
                        
                        // 6. Clean up: Detach and close the hidden tab
                        chrome.debugger.detach({ tabId: tab.id });
                        chrome.tabs.remove(tab.id);
                        resolve();
                    }
                );
            }, 2000); 
        });
    });
}