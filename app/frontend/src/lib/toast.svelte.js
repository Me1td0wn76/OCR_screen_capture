// 画面下に出る通知トースト。
// ファイル名が .svelte.js だと、ここでも $state（リアクティブ）が使える。
export const toastState = $state({ message: '', visible: false });

let timer = null;

// どのコンポーネントからでも showToast('保存しました') と呼べる。
export function showToast(message) {
  toastState.message = message;
  toastState.visible = true;
  clearTimeout(timer);
  timer = setTimeout(() => {
    toastState.visible = false;
  }, 2600);
}