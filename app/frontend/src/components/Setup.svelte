<script>
  import { onMount } from 'svelte';
  import { getStatus, postJSON, pickFolder, pollDownload, fmtMB } from '../lib/api.js';
  import { showToast } from '../lib/toast.svelte.js';

  let languages = $state([]);
  let language = $state('japan');   // 選択中の言語コード
  let modelDir = $state('');

  let busy = $state(false);          // ダウンロード中はボタンを無効化
  let showProgress = $state(false);
  let progressPct = $state(0);
  let progressText = $state('準備中…');

  onMount(async () => {
    const s = await getStatus();
    languages = s.languages;
    language = s.config.language;
    modelDir = s.model_dir;
  });

  async function browse() {
    const path = await pickFolder();
    if (path) modelDir = path;
  }

  async function start() {
    busy = true;
    showProgress = true;

    const res = await postJSON('/api/download', { language, model_dir: modelDir });
    if (!res.ok) {
      showToast(res.error || 'ダウンロードを開始できませんでした');
      busy = false;
      return;
    }

    const ok = await pollDownload(({ pct, done, total }) => {
      progressPct = pct;
      progressText =
        total > 0
          ? `ダウンロード中… ${pct}% (${fmtMB(done)} / ${fmtMB(total)})`
          : `ダウンロード中… ${fmtMB(done)}`;
    });
    if (!ok) {
      progressText = 'エラーが発生しました';
      busy = false;
      return;
    }

    // セットアップ完了をサーバに記録 → 設定画面へ遷移。
    await postJSON('/api/setup', { language, model_dir: modelDir });
    showToast('セットアップ完了！');
    setTimeout(() => {
      window.location.href = '/settings';
    }, 800);
  }
</script>

<section class="card">
  <h2><span class="step">1</span> 認識する言語を選ぶ</h2>
  <div class="lang-grid">
    {#each languages as lang}
      <label class="lang-card" class:selected={language === lang.code}>
        <input type="radio" name="language" value={lang.code} bind:group={language} />
        <span class="lang-label">{lang.label}</span>
        <span class="badge" class:ok={lang.downloaded} class:todo={!lang.downloaded}>
          {lang.downloaded ? 'DL済み' : '未DL'}
        </span>
      </label>
    {/each}
  </div>
</section>

<section class="card">
  <h2><span class="step">2</span> モデルの保存先</h2>
  <p class="hint">空欄なら既定の場所に保存します。</p>
  <div class="row gap">
    <input class="text" type="text" bind:value={modelDir} />
    <button class="btn" type="button" onclick={browse}>参照</button>
  </div>
</section>

<section class="card">
  <h2><span class="step">3</span> モデルをダウンロードして開始</h2>
  {#if showProgress}
    <div class="progress-wrap">
      <div class="progress"><div class="bar" style="width: {progressPct}%"></div></div>
      <div class="progress-text">{progressText}</div>
    </div>
  {/if}
  <button class="btn primary big" onclick={start} disabled={busy}>ダウンロードして始める </button>
</section>