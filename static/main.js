function postAction(action) {
  const url = '/api/' + action;
  updateStatus('sending ' + action + '...');
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  }).then(r => r.json().then(j => ({status: r.status, body: j}))).then(({status, body}) => {
    if (status >= 400) {
      updateStatus('error: ' + (body.message || body.error || JSON.stringify(body)));
    } else {
      updateStatus('ok: ' + JSON.stringify(body));
    }
  }).catch(err => updateStatus('fetch error: ' + err));
}

function postStop() {
  updateStatus('sending stop...');
  fetch('/api/stop', { method: 'POST' }).then(r => r.json()).then(j => updateStatus('ok: ' + JSON.stringify(j))).catch(err => updateStatus('fetch error: ' + err));
}

function toggleLed() {
  updateStatus('toggling led...');
  fetch('/api/led', { method: 'POST' }).then(r => r.json().then(j => ({status: r.status, body: j}))).then(({status, body}) => {
    if (status >= 400) {
      updateStatus('error: ' + (body.message || body.error || JSON.stringify(body)));
    } else {
      updateStatus('ok: ' + JSON.stringify(body));
    }
  }).catch(err => updateStatus('fetch error: ' + err));
}

function updateStatus(text) {
  document.getElementById('statusText').textContent = text;
}

function renderDetections(items) {
  const list = document.getElementById('detectionList');
  if (!list) return;
  list.innerHTML = '';

  if (!items || items.length === 0) {
    const li = document.createElement('li');
    li.textContent = 'none';
    list.appendChild(li);
    return;
  }

  items.forEach((d) => {
    const li = document.createElement('li');
    const conf = Number(d.confidence || 0).toFixed(2);
    li.textContent = d.label + ' (' + conf + ')';
    list.appendChild(li);
  });
}

function updateCameraStatus() {
  fetch('/api/camera/status')
    .then(r => r.json().then(body => ({ status: r.status, body })))
    .then(({ status, body }) => {
      const health = document.getElementById('cameraHealth');
      if (health) {
        if (status >= 400) {
          health.textContent = 'Camera status: error - ' + (body.error || 'unknown');
        } else {
          health.textContent = 'Camera status: ' + (body.running ? 'running' : 'starting');
        }
      }
      renderDetections(body.detections || []);
    })
    .catch(err => {
      const health = document.getElementById('cameraHealth');
      if (health) health.textContent = 'Camera status: fetch error - ' + err;
    });
}

function addPressEvents(id, action) {
  const btn = document.getElementById(id);
  btn.addEventListener('mousedown', () => postAction(action));
  btn.addEventListener('touchstart', (e) => { e.preventDefault(); postAction(action); });
  btn.addEventListener('mouseup', postStop);
  btn.addEventListener('mouseleave', postStop);
  btn.addEventListener('touchend', (e) => { e.preventDefault(); postStop(); });
}

document.addEventListener('DOMContentLoaded', () => {
  addPressEvents('forward', 'forward');
  addPressEvents('backward', 'backward');
  addPressEvents('turnRight', 'turnRight');
  addPressEvents('left', 'left');
  document.getElementById('stop').addEventListener('click', () => {
    postStop();
  });
  const ledBtn = document.getElementById('led');
  if (ledBtn) ledBtn.addEventListener('click', () => toggleLed());

  updateCameraStatus();
  setInterval(updateCameraStatus, 700);
});
