function save_options() {
  let log_url = document.getElementById('log-url').value;
  chrome.storage.sync.set({
    log_url: log_url.length > 0 ? log_url : ''
  }, () => {
    let status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(() => {
      status.textContent = '';
      window.close();
    }, 750);
  });
}

function restore_options() {
  chrome.storage.sync.get({ log_url: '' }, (items) => {
    document.getElementById('log-url').value = items.log_url;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  restore_options();
  document.getElementById('save').addEventListener('click', save_options);
});
