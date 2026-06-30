// ローカルの Flask サーバとやり取りする共通関数たち。
// ここでは DOM を触らない（値を返すだけ）。画面の更新は各コンポーネントが担当する。

// JSON を POST して、返ってきた JSON を返す。
export async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  try {
    return await res.json();
  } catch {
    return { ok: res.ok };
  }
}

// 起動時に呼ぶ。設定・言語一覧・音声一覧などの初期データを取得する。
export async function getStatus() {
  const res = await fetch('/api/status');
  return res.json();
}

// バイト数を "12.3MB" 形式に整形。
export function fmtMB(n) {
  return (n / (1024 * 1024)).toFixed(1) + 'MB';
}

// pywebview のネイティブ機能でフォルダ選択ダイアログを開く。
// （普通のブラウザで開いた時は何もせず空文字を返す。）
export async function pickFolder() {
  try {
    if (window.pywebview?.api?.pick_folder) {
      return await window.pywebview.api.pick_folder();
    }
  } catch {
    /* ignore */
  }
  return '';
}

// ダウンロードの進捗を完了/エラーまでポーリングする。
// 進行中は onProgress({ done, total, pct }) を呼ぶ。
// 成功で true、失敗で false を返す。
export async function pollDownload(onProgress) {
  while (true) {
    await new Promise((r) => setTimeout(r, 400));
    let s;
    try {
      s = await (await fetch('/api/download/status')).json();
    } catch {
      continue;
    }
    if (s.status === 'running') {
      const pct = s.total > 0 ? Math.min(100, Math.round((s.done / s.total) * 100)) : 0;
      onProgress?.({ done: s.done, total: s.total, pct });
    } else if (s.status === 'done') {
      onProgress?.({ done: 1, total: 1, pct: 100 });
      return true;
    } else if (s.status === 'error') {
      return false;
    }
  }
}