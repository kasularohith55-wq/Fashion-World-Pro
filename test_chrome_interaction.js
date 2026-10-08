const http = require('http');
const { exec, spawn } = require('child_process');
const fs = require('fs');

async function runBrowserTest() {
    console.log("Starting Chrome with Remote Debugging...");
    const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
    
    // 1. First, take a direct screenshot of the initial load state (1440x900)
    const initialCmd = `"${chromePath}" --headless=new --disable-gpu --screenshot="C:\\Users\\kasul\\Downloads\\Fashion World pro\\initial_fullscreen_hero.png" --window-size=1440,900 http://127.0.0.1:5000/`;
    
    await new Promise((resolve) => {
        exec(initialCmd, (err, stdout, stderr) => {
            console.log("Initial screenshot captured:", fs.existsSync("C:\\Users\\kasul\\Downloads\\Fashion World pro\\initial_fullscreen_hero.png"));
            resolve();
        });
    });

    // 2. Launch Chrome with CDP to test tap-to-reveal and search typing
    const chromeProc = spawn(chromePath, [
        '--headless=new',
        '--remote-debugging-port=9222',
        '--disable-gpu',
        '--no-sandbox',
        '--window-size=1440,900'
    ]);

    await new Promise(r => setTimeout(r, 1500));

    // Get CDP WebSocket URL
    http.get('http://127.0.0.1:9222/json/version', (res) => {
        let raw = '';
        res.on('data', chunk => raw += chunk);
        res.on('end', async () => {
            try {
                const info = JSON.parse(raw);
                const wsUrl = info.webSocketDebuggerUrl;
                console.log("CDP WebSocket URL:", wsUrl);
                
                const ws = new WebSocket(wsUrl);
                let id = 1;
                const send = (method, params = {}) => new Promise((resolve, reject) => {
                    const reqId = id++;
                    const handler = (event) => {
                        const msg = JSON.parse(event.data);
                        if (msg.id === reqId) {
                            ws.removeEventListener('message', handler);
                            resolve(msg.result);
                        }
                    };
                    ws.addEventListener('message', handler);
                    ws.send(JSON.stringify({ id: reqId, method, params }));
                });

                ws.onopen = async () => {
                    console.log("Connected to Chrome CDP");
                    
                    // Create new target
                    const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
                    const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
                    
                    const sessionSend = (method, params = {}) => new Promise((resolve) => {
                        const reqId = id++;
                        const handler = (event) => {
                            const msg = JSON.parse(event.data);
                            if (msg.id === reqId) {
                                ws.removeEventListener('message', handler);
                                resolve(msg.result);
                            }
                        };
                        ws.addEventListener('message', handler);
                        ws.send(JSON.stringify({ id: reqId, sessionId, method, params }));
                    });

                    await sessionSend('Page.enable');
                    await sessionSend('DOM.enable');
                    await sessionSend('Emulation.setDeviceMetricsOverride', {
                        width: 1440,
                        height: 900,
                        deviceScaleFactor: 1,
                        mobile: false
                    });

                    // Navigate to homepage
                    console.log("Navigating to homepage...");
                    await sessionSend('Page.navigate', { url: 'http://127.0.0.1:5000/' });
                    await new Promise(r => setTimeout(r, 2000));

                    // Verify initial landing state
                    const eval1 = await sessionSend('Runtime.evaluate', {
                        expression: `({
                            bodyClass: document.body.className,
                            headerMaxHeight: window.getComputedStyle(document.querySelector('.storefront-header-master')).maxHeight,
                            headerOpacity: window.getComputedStyle(document.querySelector('.storefront-header-master')).opacity,
                            heroHeight: window.getComputedStyle(document.querySelector('.main-hero-cinematic')).height
                        })`,
                        returnByValue: true
                    });
                    console.log("INITIAL STATE EVALUATION:", eval1.result.value);

                    // Step 2: Click on the hero banner to reveal header
                    console.log("Clicking hero banner to reveal header...");
                    await sessionSend('Runtime.evaluate', {
                        expression: `document.querySelector('.main-hero-cinematic').click()`
                    });
                    await new Promise(r => setTimeout(r, 1200));

                    // Verify revealed state
                    const eval2 = await sessionSend('Runtime.evaluate', {
                        expression: `({
                            bodyClass: document.body.className,
                            headerMaxHeight: window.getComputedStyle(document.querySelector('.storefront-header-master')).maxHeight,
                            headerOpacity: window.getComputedStyle(document.querySelector('.storefront-header-master')).opacity,
                            heroHeight: window.getComputedStyle(document.querySelector('.main-hero-cinematic')).height
                        })`,
                        returnByValue: true
                    });
                    console.log("REVEALED STATE EVALUATION:", eval2.result.value);

                    // Capture Revealed Screenshot
                    const ss1 = await sessionSend('Page.captureScreenshot', { format: 'png' });
                    fs.writeFileSync('C:\\Users\\kasul\\Downloads\\Fashion World pro\\revealed_website_layout.png', Buffer.from(ss1.data, 'base64'));
                    console.log("Revealed website screenshot captured!");

                    // Step 3: Type 'mens' in search bar to test live autocomplete
                    console.log("Typing 'mens' in search input...");
                    await sessionSend('Runtime.evaluate', {
                        expression: `
                            const input = document.querySelector('#storefrontSearchForm input[name="query"]');
                            input.focus();
                            input.value = 'mens';
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        `
                    });
                    await new Promise(r => setTimeout(r, 800));

                    const eval3 = await sessionSend('Runtime.evaluate', {
                        expression: `({
                            dropdownShown: document.getElementById('searchSuggestionsDropdown').classList.contains('show'),
                            dropdownHtmlLength: document.getElementById('searchSuggestionsDropdown').innerHTML.length,
                            catItemsCount: document.querySelectorAll('.suggestion-cat-item').length,
                            prodItemsCount: document.querySelectorAll('.suggestion-prod-item').length
                        })`,
                        returnByValue: true
                    });
                    console.log("LIVE AUTOCOMPLETE EVALUATION:", eval3.result.value);

                    // Capture Autocomplete Screenshot
                    const ss2 = await sessionSend('Page.captureScreenshot', { format: 'png' });
                    fs.writeFileSync('C:\\Users\\kasul\\Downloads\\Fashion World pro\\search_autocomplete_mens.png', Buffer.from(ss2.data, 'base64'));
                    console.log("Live Autocomplete screenshot captured!");

                    // Step 4: Test mobile viewport
                    await sessionSend('Emulation.setDeviceMetricsOverride', {
                        width: 390,
                        height: 844,
                        deviceScaleFactor: 2,
                        mobile: true
                    });
                    await sessionSend('Page.navigate', { url: 'http://127.0.0.1:5000/' });
                    await new Promise(r => setTimeout(r, 1500));
                    
                    const ssMobileInit = await sessionSend('Page.captureScreenshot', { format: 'png' });
                    fs.writeFileSync('C:\\Users\\kasul\\Downloads\\Fashion World pro\\mobile_fullscreen_hero.png', Buffer.from(ssMobileInit.data, 'base64'));

                    await sessionSend('Runtime.evaluate', {
                        expression: `document.querySelector('.main-hero-cinematic').click()`
                    });
                    await new Promise(r => setTimeout(r, 1000));

                    const ssMobileRev = await sessionSend('Page.captureScreenshot', { format: 'png' });
                    fs.writeFileSync('C:\\Users\\kasul\\Downloads\\Fashion World pro\\mobile_revealed_layout.png', Buffer.from(ssMobileRev.data, 'base64'));
                    console.log("Mobile screenshots captured!");

                    ws.close();
                    chromeProc.kill();
                    console.log("ALL BROWSER TESTS AND SCREENSHOTS COMPLETED!");
                    process.exit(0);
                };
            } catch(e) {
                console.error("Error in CDP test:", e);
                chromeProc.kill();
                process.exit(1);
            }
        });
    });
}

runBrowserTest();
