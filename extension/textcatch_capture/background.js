// 요청한 탭(현재 보이는 화면)을 PNG 로 찍어서 돌려준다.
// 요청은 content_scripts.matches 에 등록된 사이트(텍스트 캐치)에서만 들어온다.
// (captureVisibleTab 은 <all_urls> 권한이 있어야 패널 안의 다른 사이트까지 찍을 수 있음)
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || msg.type !== 'capture' || !sender.tab) return;
    chrome.tabs.captureVisibleTab(sender.tab.windowId, { format: 'png' })
        .then((dataUrl) => sendResponse({ dataUrl }))
        .catch((err) => sendResponse({ error: String(err && err.message || err) }));
    return true;   // 비동기 응답
});
