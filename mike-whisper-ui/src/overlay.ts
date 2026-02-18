import { listen } from '@tauri-apps/api/event';
import { getCurrentWebviewWindow } from '@tauri-apps/api/webviewWindow';

const container = document.getElementById('text-container');
const overlayWindow = getCurrentWebviewWindow();

listen('overlay-event', (event) => {
    try {
        const payload = JSON.parse(event.payload as string);

        if (payload.type === 'STATUS') {
            if (payload.data === 'RECORDING') {
                if (container) container.innerHTML = '<i>Listening...</i>';
                if (container) container.classList.add('active');
                overlayWindow.show();
            } else if (payload.data === 'IDLE' || payload.data === 'NO_SPEECH') {
                setTimeout(() => {
                    if (container) container.classList.remove('active');
                    setTimeout(() => overlayWindow.hide(), 300);
                }, 2000);
            }
        } else if (payload.type === 'PARTIAL_RESULT') {
            if (container) container.innerHTML = `<span class="partial">${payload.data}</span>`;
            if (container) container.classList.add('active');
            overlayWindow.show();
        } else if (payload.type === 'RESULT') {
            if (container) container.innerHTML = `<span>${payload.data}</span>`;
            if (container) container.classList.add('active');
        }
    } catch (e) {
        console.error("Overlay parse error", e);
    }
});
