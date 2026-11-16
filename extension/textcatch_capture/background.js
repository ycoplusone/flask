// 화면캡쳐 담당
//   - 'self'  : 텍스트 캐치 화면(요청한 탭)을 찍어서 돌려줌
//   - 'popup' : 텍스트 캐치 화면이 연 새 창(팝업)을 찍어서 돌려줌
//   - 새 창의 📷 버튼 / 단축키(Alt+Shift+S) : 그 새 창을 찍어서 텍스트 캐치 화면으로 보내고 앞으로 가져옴
// (captureVisibleTab 은 <all_urls> 권한이 있어야 다른 사이트 화면까지 찍을 수 있음)

// 텍스트 캐치 사이트 (manifest.json 의 content_scripts.matches 와 같게 유지)
const TEXTCATCH_HOSTS = ['enfish.duckdns.org', '168.107.55.147', 'localhost', '127.0.0.1'];

function isTextcatchUrl(url) {
    try {
        const u = new URL(url);
        return u.protocol.startsWith('http') && TEXTCATCH_HOSTS.includes(u.hostname);
    } catch (e) {
        return false;
    }
}

// 텍스트 캐치 화면이 연 새 창이면 그 텍스트 캐치 탭을, 아니면 null
async function getTextcatchOpener(tab) {
    if (!tab || tab.openerTabId === undefined) return null;
    try {
        const opener = await chrome.tabs.get(tab.openerTabId);
        return isTextcatchUrl(opener.url) ? opener : null;
    } catch (e) {
        return null;   // 텍스트 캐치 화면이 이미 닫힘
    }
}

function capture(windowId) {
    return chrome.tabs.captureVisibleTab(windowId, { format: 'png' });
}

// openerTabId 가 텍스트 캐치 탭인 새 창 중 가장 최근 것
async function findPopupTab(openerTabId) {
    const tabs = await chrome.tabs.query({});
    const popups = tabs.filter(t => t.openerTabId === openerTabId);
    if (!popups.length) return null;
    popups.sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));
    return popups[0];
}

// 찍은 결과를 텍스트 캐치 화면으로 보내고 그 화면을 앞으로 가져옴
async function sendToOpener(opener, payload) {
    try {
        await chrome.tabs.sendMessage(opener.id, { type: 'popupCapture', ...payload });
        await chrome.windows.update(opener.windowId, { focused: true });
        await chrome.tabs.update(opener.id, { active: true });
    } catch (e) {
        // 텍스트 캐치 화면을 새로고침 전이라 content.js 가 없는 경우 등 → 무시
    }
}

// 새 창을 찍어서 텍스트 캐치 화면으로 보냄. 반환: 오류 메시지 또는 null
async function capturePopupToOpener(tab) {
    const opener = await getTextcatchOpener(tab);
    if (!opener) return '텍스트 캐치 화면이 연 창이 아니거나, 텍스트 캐치 화면이 닫혔습니다.';
    let payload;
    try {
        payload = { dataUrl: await capture(tab.windowId) };
    } catch (err) {
        payload = { error: String(err && err.message || err) };
    }
    await sendToOpener(opener, payload);
    return payload.error || null;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || !sender.tab) return;

    // 텍스트 캐치 화면에서 요청 (content.js)
    if (msg.type === 'capture') {
        (async () => {
            if (msg.mode === 'popup') {
                const popup = await findPopupTab(sender.tab.id);
                if (!popup) throw new Error('열려 있는 새 창이 없습니다.');
                return capture(popup.windowId);
            }
            return capture(sender.tab.windowId);
        })()
            .then((dataUrl) => sendResponse({ dataUrl }))
            .catch((err) => sendResponse({ error: String(err && err.message || err) }));
        return true;   // 비동기 응답
    }

    // 새 창의 📷 버튼 (popup_button.js)
    if (msg.type === 'popupButtonCapture') {
        capturePopupToOpener(sender.tab).then((error) => sendResponse({ error }));
        return true;
    }
});

// 단축키: 새 창에서 누르면 그 창을 찍어 텍스트 캐치 화면으로 보냄
chrome.commands.onCommand.addListener(async (command, tab) => {
    if (command !== 'capture-popup' || !tab) return;
    if (await getTextcatchOpener(tab)) await capturePopupToOpener(tab);
});

// 텍스트 캐치 화면이 연 새 창에 페이지가 열릴 때마다 📷 버튼 넣기 (다른 창/탭에는 넣지 않음)
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    if (changeInfo.status !== 'complete' || !tab.url || !tab.url.startsWith('http')) return;
    if (!(await getTextcatchOpener(tab))) return;
    try {
        await chrome.scripting.executeScript({ target: { tabId }, files: ['popup_button.js'] });
    } catch (e) {
        // 크롬 내부 페이지 등 넣을 수 없는 화면 → 무시
    }
});
