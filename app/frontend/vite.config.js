import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';

export default defineConfig({
  plugins: [svelte()],

  // 生成されるJS/CSSの参照パスの接頭辞。
  // Flask は static/ を "/static" で配信するので、その下の dist を指す。
  base: '/static/dist/',

  build: {
    // ビルド成果物の出力先を、Pythonアプリ側の static/dist に直接出す。
    outDir: resolve(__dirname, '../app/web/static/dist'),
    emptyOutDir: true,   // ビルドのたびに dist を空にしてから出力
  },
});