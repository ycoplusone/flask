// 텍스트 캐치 화면이 연 새 창(팝업)에 띄우는 📷 캡쳐 버튼
//   background.js 가 해당 새 창에만 넣어 준다. (다른 사이트 화면이므로 Shadow DOM 으로 스타일 격리)
//   누르면 버튼을 잠깐 숨기고 새 창을 찍어 텍스트 캐치 화면으로 보낸다.
(() => {
    if (window.__textcatchCaptureButton) return;   // 같은 페이지에 중복 삽입 방지
    window.__textcatchCaptureButton = true;

    const host = document.createElement('div');
    host.style.cssText = 'all: initial; position: fixed; right: 16px; bottom: 16px; z-index: 2147483647;';
    const root = host.attachShadow({ mode: 'closed' });
    root.innerHTML = `
        <style>
            button {
                padding: 10px 14px;
                border: none;
                border-radius: 24px;
                background: #e74c3c;
                color: #fff;
                font: bold 14px sans-serif;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
                cursor: pointer;
                opacity: 0.9;
            }
            button:hover { opacity: 1; background: #c0392b; }
            button:disabled { background: #999; cursor: wait; }
        </style>
        <button type="button" title="이 창을 캡쳐해서 텍스트 캐치 화면으로 보내기 (Alt+Shift+S)">📷 캡쳐</button>
    `;
    const btn = root.querySelector('button');

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        host.style.visibility = 'hidden';                      // 버튼이 캡쳐에 찍히지 않도록 숨김
        await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        await new Promise(r => setTimeout(r, 80));             // 숨긴 화면이 실제로 그려질 때까지 대기
        chrome.runtime.sendMessage({ type: 'popupButtonCapture' }, (res) => {
            host.style.visibility = '';
            btn.disabled = false;
            const error = chrome.runtime.lastError ? chrome.runtime.lastError.message : (res && res.error);
            if (error) alert('캡쳐 실패: ' + error);
        });
    });

    (document.body || document.documentElement).appendChild(host);
})();
