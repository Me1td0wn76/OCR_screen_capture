import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';

// index.html の <div id="app"> の中に App コンポーネントを描画する。
const app = mount(App, {
  target: document.getElementById('app'),
});

export default app;