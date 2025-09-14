let tab_listeners = {};
let tab_push = {};
let tab_lasturl = {};
let selectedId = -1;

function refreshCount() {
  let txt = tab_listeners[selectedId] ? tab_listeners[selectedId].length : 0;
  chrome.tabs.get(selectedId, () => {
    if (!chrome.runtime.lastError) {
      chrome.action.setBadgeText({ text: txt ? '' + txt : '', tabId: selectedId });
      if (txt > 0) {
        chrome.action.setBadgeBackgroundColor({ color: [255, 0, 0, 255] });
      } else {
        chrome.action.setBadgeBackgroundColor({ color: [0, 0, 255, 0] });
      }
    }
  });
}

function logListener(data) {
  chrome.storage.sync.get({ log_url: '' }, (items) => {
    let log_url = items.log_url;
    if (!log_url.length) return;
    try {
      fetch(log_url, {
        method: 'POST',
        headers: { "Content-type": "application/json; charset=UTF-8" },
        body: JSON.stringify(data)
      }).catch(() => {});
    } catch (e) {}
  });
}

chrome.runtime.onMessage.addListener((msg, sender) => {
  let tabId = sender.tab?.id;
  if (!tabId) return;

  if (msg.listener) {
    if (msg.listener === 'function () { [native code] }') return;
    msg.parent_url = sender.tab.url;
    if (!tab_listeners[tabId]) tab_listeners[tabId] = [];
    tab_listeners[tabId].push(msg);
    logListener(msg);
  }

  if (msg.pushState) {
    tab_push[tabId] = true;
  }

  if (msg.changePage) {
    delete tab_lasturl[tabId];
  }

  if (msg.log) {
    console.log(msg.log);
  } else {
    refreshCount();
  }
});

chrome.tabs.onUpdated.addListener((tabId, props) => {
  if (props.status === "complete") {
    if (tabId === selectedId) refreshCount();
  } else if (props.status) {
    if (tab_push[tabId]) {
      delete tab_push[tabId];
    } else {
      if (!tab_lasturl[tabId]) {
        tab_listeners[tabId] = [];
      }
    }
  }
  if (props.status === "loading") tab_lasturl[tabId] = true;
});

chrome.tabs.onActivated.addListener((activeInfo) => {
  selectedId = activeInfo.tabId;
  refreshCount();
});

chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs.length) {
    selectedId = tabs[0].id;
    refreshCount();
  }
});

chrome.runtime.onConnect.addListener((port) => {
  port.onMessage.addListener((msg) => {
    if (msg === "get-stuff") {
      port.postMessage({ listeners: tab_listeners });
    }
    if (msg === "clear-stuff") {
      tab_listeners = {};
      refreshCount();
      port.postMessage({ listeners: tab_listeners });
    }
  });
});
