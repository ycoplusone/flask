// 텍스트 캐치 페이지 <-> 확장 프로그램 중계
//   페이지가 window.postMessage 로 캡쳐를 요청하면 background 에 전달하고,
//   찍은 이미지(dataURL)를 다시 페이지로 돌려준다.

// 페이지에서 확장 프로그램 설치 여부를 알 수 있도록 표시 (DOM 은 페이지와 공유됨)
document.documentElement.dataset.textcatchCapture = '1';

// 페이지 → 확장 프로그램 : 캡쳐 요청 (mode: 'self' 현재 탭 / 'popup' 이 화면이 연 새 창)
window.addEventListener('message', (e) => {
    if (e.source !== window || !e.data || e.data.type !== 'TEXTCATCH_CAPTURE_REQ') return;
    const id = e.data.id;
    chrome.runtime.sendMessage({ type: 'capture', mode: e.data.mode || 'self' }, (res) => {
        const error = chrome.runtime.lastError ? chrome.runtime.lastError.message : (res && res.error);
        window.postMessage({
            type: 'TEXTCATCH_CAPTURE_RES',
            id,
            dataUrl: res && res.dataUrl,
            error: error || null,
        }, window.location.origin);
    });
});

// 확장 프로그램 → 페이지 : 새 창에서 단축키로 찍은 이미지 전달
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || msg.type !== 'popupCapture') return;
    window.postMessage({
        type: 'TEXTCATCH_POPUP_CAPTURE',
        dataUrl: msg.dataUrl || null,
        error: msg.error || null,
    }, window.location.origin);
    sendResponse({ ok: true });
});
