<script>
  import Setup from './components/Setup.svelte';
  import Settings from './components/Settings.svelte';

  // Flask は /setup と /settings の両方でこの同じ index.html を返す。
  // どちらの画面かは「今のURLパス」で判定する（ルーターは使わない）。
  const isSetup = window.location.pathname.startsWith('/setup');

  // ヘッダーの文言は画面ごとに変える。
  const tagline = isSetup
    ? 'はじめまして！まずは言語を選んでね'
    : '設定をカスタマイズ';
</script>

<div class="bg-blobs"><span></span><span></span><span></span></div>

<main class="wrap">
  <header class="hero">
    <div class="mascot"></div>
    <div>
      <h1>OCR スクリーンキャプチャ</h1>
      <p class="tagline">{tagline}</p>
    </div>
  </header>

  {#if isSetup}
    <Setup />
  {:else}
    <Settings />
  {/if}

  <footer class="foot">made with Me1td0wn76</footer>
</main>
<div class="toast" class:show={toastState.visible}>{toastState.message}</div>