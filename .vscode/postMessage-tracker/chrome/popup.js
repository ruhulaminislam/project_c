let port = chrome.runtime.connect({ name: "postMessagePort" });

function loaded() {
  port.postMessage("get-stuff");
  port.onMessage.addListener((msg) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      let selectedId = tabs[0].id;
      listListeners(msg.listeners[selectedId] || []);
    });
  });

  document.getElementById('refresh').addEventListener('click', () => {
    port.postMessage("get-stuff");
  });

  document.getElementById('clear').addEventListener('click', () => {
    port.postMessage("clear-stuff");
  });

  document.getElementById('export').addEventListener('click', () => {
    chrome.storage.local.get(null, (items) => {
      let data = JSON.stringify(items, null, 2);
      let blob = new Blob([data], { type: 'application/json' });
      let url = URL.createObjectURL(blob);
      chrome.downloads.download({
        url: url,
        filename: "postMessage_logs.json"
      });
    });
  });
}

window.onload = loaded;

function listListeners(listeners) {
  let x = document.getElementById('x');
  x.innerHTML = '';
  document.getElementById('h').innerText = listeners.length
    ? `Listeners found: ${listeners.length}`
    : 'No listeners detected.';

  listeners.forEach((l) => {
    let li = document.createElement('li');
    li.innerHTML = `<span>${l.parent_url || ''}</span><pre>${l.listener}</pre>`;
    x.appendChild(li);
  });
}
