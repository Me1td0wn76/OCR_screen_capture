// Shared helpers for the OCR tool web UI.

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  try { return await res.json(); }
  catch { return { ok: res.ok }; }
}

let _toastTimer = null;
function toast(msg) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

function fmtMB(n) { return (n / (1024 * 1024)).toFixed(1) + 'MB'; }

// Poll the download status endpoint until done/error. Updates #bar / #progressText.
async function pollDownload() {
  const bar = document.getElementById('bar');
  const txt = document.getElementById('progressText');
  while (true) {
    await new Promise(r => setTimeout(r, 400));
    let s;
    try { s = await (await fetch('/api/download/status')).json(); }
    catch { continue; }
    if (s.status === 'running') {
      if (s.total > 0) {
        const pct = Math.min(100, Math.round(s.done / s.total * 100));
        if (bar) bar.style.width = pct + '%';
        if (txt) txt.textContent = `ダウンロード中… ${pct}% (${fmtMB(s.done)} / ${fmtMB(s.total)})`;
      } else if (txt) {
        txt.textContent = `ダウンロード中… ${fmtMB(s.done)}`;
      }
    } else if (s.status === 'done') {
      if (bar) bar.style.width = '100%';
      if (txt) txt.textContent = '完了！';
      return true;
    } else if (s.status === 'error') {
      if (txt) txt.textContent = 'エラー: ' + (s.error || '不明');
      toast('ダウンロードに失敗しました');
      return false;
    }
  }
}
