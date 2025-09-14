let injectedJS = function (pushstate, msgeventlistener, msgporteventlistener) {
  let originalFunctionToString = Function.prototype.toString;

  let m = function (detail) {
    let storeEvent = new CustomEvent('postMessageTracker', { detail: detail });
    document.dispatchEvent(storeEvent);
  };

  // Hijack pushState
  let oldPushState = pushstate;
  pushstate = function () {
    m({ pushState: true });
    return oldPushState.apply(this, arguments);
  };
  History.prototype.pushState = pushstate;

  // Intercept addEventListener
  let oldAdd = msgeventlistener;
  Window.prototype.addEventListener = function (type, listener, options) {
    if (type === "message") {
      m({ listener: listener.toString() });
    }
    return oldAdd.apply(this, arguments);
  };

  // Intercept MessagePort
  let oldPortAdd = msgporteventlistener;
  MessagePort.prototype.addEventListener = function (type, listener, options) {
    if (type === "message") {
      m({ listener: listener.toString() });
    }
    return oldPortAdd.apply(this, arguments);
  };
};

injectedJS = '(' + injectedJS.toString() + ')'
  + '(History.prototype.pushState, Window.prototype.addEventListener, MessagePort.prototype.addEventListener)';

document.addEventListener('postMessageTracker', (event) => {
  chrome.runtime.sendMessage(event.detail);
});

// track page changes
window.addEventListener('beforeunload', () => {
  let storeEvent = new CustomEvent('postMessageTracker', { detail: { changePage: true } });
  document.dispatchEvent(storeEvent);
});

(function () {
  if (document.contentType === 'application/xml') return;
  let script = document.createElement("script");
  script.setAttribute('type', 'text/javascript');
  script.appendChild(document.createTextNode(injectedJS));
  document.documentElement.appendChild(script);
})();
