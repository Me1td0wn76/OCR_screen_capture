<script>
  import { onMount } from 'svelte';
  import { getStatus, postJSON, pickFolder, pollDownload, fmtMB } from '../lib/api.js';
  import { showToast } from '../lib/toast.svelte.js';

  // サーバから取得する状態。最初は null にして「読込前」を表す。
  let cfg = $state(null);
  let languages = $state([]);
  let voices = $state([]);
  let modelDir = $state('');
  let llmAvailable = $state(false);

  // ダウンロード進捗の表示用。
  let showProgress = $state(false);
  let progressPct = $state(0);
  let progressText = $state('');

  // コンポーネントが画面に出た直後に1回だけ実行される。
  onMount(async () => {
    const s = await getStatus();
    cfg = s.config;
    languages = s.languages;
    voices = s.voices;
    modelDir = s.model_dir;       // 解決済みの保存先（cfg.model_dir とは別物）
    llmAvailable = s.llm_available;

    // 保存済みの声（部分一致の文字列）を、実際の音声フルネームに解決して選択状態に。
    if (cfg.tts.voice_match) {
      const hit = voices.find((v) => v.name.includes(cfg.tts.voice_match));
      if (hit) cfg.tts.voice_match = hit.name;
    }
  });

  async function runAction(name) {
    await postJSON('/api/action/' + name, {});
    showToast('実行しました');
  }

  async function browse() {
    const path = await pickFolder();
    if (path) modelDir = path;
  }

  async function download() {
    showProgress = true;
    const res = await postJSON('/api/download', { language: cfg.language, model_dir: modelDir });
    if (!res.ok) {
      showToast(res.error || '開始できませんでした');
      return;
    }
    const ok = await pollDownload(({ pct, done, total }) => {
      progressPct = pct;
      progressText =
        total > 0
          ? `ダウンロード中… ${pct}% (${fmtMB(done)} / ${fmtMB(total)})`
          : `ダウンロード中… ${fmtMB(done)}`;
    });
    if (ok) {
      progressPct = 100;
      progressText = '完了！';
      showToast('ダウンロード完了！');
      const lang = languages.find((l) => l.code === cfg.language);
      if (lang) lang.downloaded = true;   // バッジを「DL済み」に更新
    } else {
      showToast('ダウンロードに失敗しました');
    }
  }

  async function save() {
    await postJSON('/api/settings', {
      language: cfg.language,
      model_dir: modelDir,
      auto_ocr: cfg.auto_ocr,
      copy_to_clipboard: cfg.copy_to_clipboard,
      show_notifications: cfg.show_notifications,
      tts: {
        speak_on_ocr: cfg.tts.speak_on_ocr,
        voice_match: cfg.tts.voice_match,
        rate: cfg.tts.rate,
      },
      translate: {
        enabled: cfg.translate.enabled,
        base_url: cfg.translate.base_url.trim(),
        model: cfg.translate.model.trim(),
        target_lang: cfg.translate.target_lang.trim(),
      },
    });
    showToast('保存しました ');
  }
</script>

{#if cfg}
  <section class="card">
    <h2>クイック操作</h2>
    <div class="row gap">
      <button class="btn" onclick={() => runAction('ocr_clipboard')}> クリップボード画像をOCR</button>
      <button class="btn" onclick={() => runAction('speak_last')}> 直近を読み上げ</button>
      <button class="btn" onclick={() => runAction('translate_last')}> 直近を翻訳</button>
    </div>
  </section>

  <section class="card">
    <h2>言語とモデル</h2>
    <div class="lang-grid">
      {#each languages as lang}
        <label class="lang-card" class:selected={cfg.language === lang.code}>
          <input type="radio" name="language" value={lang.code} bind:group={cfg.language} />
          <span class="lang-label">{lang.label}</span>
          <span class="badge" class:ok={lang.downloaded} class:todo={!lang.downloaded}>
            {lang.downloaded ? 'DL済み' : '未DL'}
          </span>
        </label>
      {/each}
    </div>

    <label class="field"><span>モデル保存先</span>
      <div class="row gap">
        <input class="text" type="text" bind:value={modelDir} />
        <button class="btn" type="button" onclick={browse}>参照</button>
      </div>
    </label>

    {#if showProgress}
      <div class="progress-wrap">
        <div class="progress"><div class="bar" style="width: {progressPct}%"></div></div>
        <div class="progress-text">{progressText}</div>
      </div>
    {/if}

    <button class="btn" onclick={download}>選択言語のモデルをダウンロード/再取得</button>
  </section>

  <section class="card">
    <h2>動作</h2>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.auto_ocr} />
      <span>自動OCR（クリップボード監視）</span></label>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.copy_to_clipboard} />
      <span>結果をクリップボードへコピー</span></label>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.show_notifications} />
      <span>通知を表示</span></label>
  </section>

  <section class="card">
    <h2>読み上げ (TTS)</h2>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.tts.speak_on_ocr} />
      <span>OCR後に自動で読み上げ</span></label>
    <label class="field"><span>音声</span>
      <select class="text" bind:value={cfg.tts.voice_match}>
        {#each voices as v}
          <option value={v.name}>{v.name}</option>
        {/each}
      </select>
    </label>
    <label class="field"><span>速度: <b>{cfg.tts.rate}</b></span>
      <input type="range" min="80" max="320" bind:value={cfg.tts.rate} />
    </label>
  </section>

  <section class="card">
    <h2>翻訳 (LocalLLM)
      <span class="badge" class:ok={llmAvailable} class:todo={!llmAvailable}>
        {llmAvailable ? '接続OK' : '未接続'}</span>
    </h2>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.translate.enabled} />
      <span>OCR後に自動翻訳</span></label>
    <label class="field"><span>エンドポイント (OpenAI互換)</span>
      <input class="text" type="text" bind:value={cfg.translate.base_url} /></label>
    <label class="field"><span>モデル名</span>
      <input class="text" type="text" bind:value={cfg.translate.model} /></label>
    <label class="field"><span>翻訳先の言語</span>
      <input class="text" type="text" bind:value={cfg.translate.target_lang} /></label>
  </section>

  <div class="save-bar">
    <button class="btn primary big" onclick={save}>設定を保存 </button>
  </div>
{/if}
