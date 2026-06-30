<script>
  import { onMount } from 'svelte';
  import { getStatus, postJSON } from '../lib/api.js';
  import { showToast } from '../lib/toast.svelte.js';

  // サーバから取得する状態。最初は null にして「読込前」を表す。
  let cfg = $state(null);
  let voices = $state([]);
  let llmAvailable = $state(false);

  // サーバの現在の状態を取り込む（トレイ/ホットキーでの変更も反映するため、
  // 表示・フォーカスのたびに呼び直す）。
  async function load() {
    const s = await getStatus();
    cfg = s.config;
    voices = s.voices;
    llmAvailable = s.llm_available;

    // 保存済みの声（部分一致の文字列）を、実際の音声フルネームに解決して選択状態に。
    if (cfg.tts.voice_match) {
      const hit = voices.find((v) => v.name.includes(cfg.tts.voice_match));
      if (hit) cfg.tts.voice_match = hit.name;
    }

    // hotkeys が無い古い config への保険（config.py の DEFAULTS に追加されるまで）。
    if (!cfg.hotkeys) cfg.hotkeys = {};
    if (!cfg.hotkeys.toggle_auto_ocr) {
      cfg.hotkeys.toggle_auto_ocr = { enabled: true, combo: 'ctrl+shift+o' };
    }
  }

  onMount(() => {
    load();
    // トレイメニューやホットキーで状態が変わったあと、ウィンドウに戻ってきたら
    // 最新の設定を取り直して表示を一致させる（古い値で上書き保存するのを防ぐ）。
    const resync = () => load();
    const onVisible = () => {
      if (document.visibilityState === 'visible') load();
    };
    window.addEventListener('focus', resync);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.removeEventListener('focus', resync);
      document.removeEventListener('visibilitychange', onVisible);
    };
  });

  async function runAction(name) {
    await postJSON('/api/action/' + name, {});
    showToast('実行しました');
  }

  async function save() {
    await postJSON('/api/settings', {
      language: cfg.language,
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
      hotkeys: {
        toggle_auto_ocr: {
          enabled: cfg.hotkeys.toggle_auto_ocr.enabled,
          combo: cfg.hotkeys.toggle_auto_ocr.combo,
        },
      },
    });
    showToast('保存しました ');
  }

  // --- ショートカットキー入力（e.code で安定取得 → "ctrl+shift+o" に正規化）---
  function comboFromEvent(e) {
    const mods = [];
    if (e.ctrlKey) mods.push('ctrl');
    if (e.shiftKey) mods.push('shift');
    if (e.altKey) mods.push('alt');
    if (e.metaKey) mods.push('win');
    const c = e.code;
    let key = '';
    if (/^Key[A-Z]$/.test(c)) key = c.slice(3).toLowerCase();
    else if (/^Digit[0-9]$/.test(c)) key = c.slice(5);
    else if (/^F([1-9]|1[0-2])$/.test(c)) key = c.toLowerCase();
    else {
      const named = {
        Space: 'space', Enter: 'enter', Tab: 'tab', Escape: 'esc',
        Backspace: 'backspace', Delete: 'delete', Insert: 'insert',
        Home: 'home', End: 'end', PageUp: 'pageup', PageDown: 'pagedown',
        ArrowLeft: 'left', ArrowUp: 'up', ArrowRight: 'right', ArrowDown: 'down',
      };
      key = named[c] || '';
    }
    if (!key || mods.length === 0) return null; // 修飾キー必須＋本体キー1つ
    return [...mods, key].join('+');
  }

  function captureHotkey(e) {
    e.preventDefault();
    const combo = comboFromEvent(e);
    if (combo) cfg.hotkeys.toggle_auto_ocr.combo = combo;
  }

  // 表示用: "ctrl+shift+o" -> "Ctrl+Shift+O"
  const prettify = (s) =>
    (s || '')
      .split('+')
      .map((p) => (p.length <= 1 ? p.toUpperCase() : p[0].toUpperCase() + p.slice(1)))
      .join('+');
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
    <h2>動作</h2>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.auto_ocr} />
      <span>自動OCR（クリップボード監視）</span></label>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.copy_to_clipboard} />
      <span>結果をクリップボードへコピー</span></label>
    <label class="toggle"><input type="checkbox" bind:checked={cfg.show_notifications} />
      <span>通知を表示</span></label>
  </section>

  <section class="card">
    <h2>ショートカットキー</h2>
    <label class="toggle">
      <input type="checkbox" bind:checked={cfg.hotkeys.toggle_auto_ocr.enabled} />
      <span>自動OCRのON/OFFをショートカットで切り替える</span>
    </label>
    <label class="field"><span>キー（入力欄を選んで押す）</span>
      <input
        class="text"
        type="text"
        readonly
        placeholder="例: Ctrl+Shift+O"
        value={prettify(cfg.hotkeys.toggle_auto_ocr.combo)}
        onkeydown={captureHotkey}
      />
    </label>
    <p class="hint">修飾キー（Ctrl / Shift / Alt / Win）＋ キーを1つ。例: Ctrl+Shift+O</p>
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
