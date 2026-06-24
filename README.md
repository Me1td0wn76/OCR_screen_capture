# OCR_SCREEN_CAPTURE_TRANSCRIPTION
##　説明  
これは、スクリーンキャプチャした画像から文字を抽出し、テキストに変換するOCR（光学文字認識）ツールです。  
また、抽出したテキストを音声に変換することも可能です。  
## やりたいこと
- スクリーンキャプチャした画像から文字を抽出し、テキストに変換する  
- 抽出したテキストを音声に変換する  
- 抽出したテキストをクリップボードにコピーする  
- またこれをexe化して、Windowsで簡単に使えるようにする  
- cpuで動作するようにする(できるだけ軽くね)  
- トレイに常駐させて、スクリーンショットを撮ると自動で文字を抽出してくれるようにする  
- できれば、スクリーンショットはwin+shift+sのwindowsの標準のスクリーンショットの機能に上乗せする形で、スクリーンショットを撮ったら自動で文字を抽出してくれるようにしたいです。  
- LocalLLM起動中は、翻訳もできるようにしたいです。  

# 使用技術  
- python3.14.3
- flask
- 軽量のOCRライブラリ（例：pytesseract）
- etc...
- exe化にはpyinstallerかな
  
model folder は自分のlocateを初期設定時にconfigで(configはUIで設定可能)指定できるようにする予定!  
またそれに合わせてmodelの取得または初期セットアップ時の言語を変更するようにする！  
setupは、初回起動時にUIで設定できるようにしたい！  
その時にmodelの取得または初期セットアップ時の言語を変更するようにする！  
ソースコードはappフォルダからの階層構造にする！  
UIは可愛くしたいよね  
exeでSETUPするときは\username\AppData\Local\Programs\OCR_SCREEN_CAPTURE_TRANSCRIPTIONにインストールされるようにしたい！  
これならUACに引っかからんやろ。たぶん。
SetupはWeb上で表示させないようにする！
UIだけはWebと同じ感じにしたいでも、Web上で表示させないようにする！これやね。
pywebviewを使うと、Web上で表示させないようにできるらしい。これか...

---

# 実装ガイド（開発者向け）

上記の要望に沿って実装したトレイ常駐アプリです。**CPUのみ・外部OCRバイナリ不要**で動作します。

## できること（実装済み・動作確認済み）

- **自動OCR**: `Win+Shift+S` のスニップ→クリップボード画像を自動検知してOCR
- **クリップボードへコピー** / **読み上げ(オフラインTTS, SAPI5)** / **翻訳(ローカルLLM起動時)**
- **トレイ常駐**（pystray）+ 通知
- **初回セットアップUI / 設定UI**: 可愛いHTML/CSSを **pywebviewのネイティブ窓** に表示（ブラウザは開かない。localhostサーバは埋め込みWebViewのみが利用）
- **言語選択 + モデル自動DL**: 日本語/英語/中国語/韓国語。設定UIから選択→ONNXモデルを自動ダウンロード（進捗バー付き）
- **モデル保存先の指定**: 設定UIの「参照」（ネイティブのフォルダ選択）でconfigに保存
- **exe化**（PyInstaller, ワンフォルダ）+ **per-userインストーラ**（Inno Setup, `%LocalAppData%\Programs` へ、UAC回避）

> 日本語認識は RapidOCR 同梱の中国語モデルではかな精度が低いため、日本語モデル
> `japan_rec_crnn_v2.onnx`（入力高さ32）に差し替えています。

## ソース構成（`app/` 階層）

```
main.py                 エントリ（トレイ別スレッド + pywebviewはメインスレッド）
app/
  controller.py         OCR→コピー/TTS/翻訳のとりまとめ + 設定API
  ocr.py                RapidOCRラッパ（言語別モデルを解決, CPU）
  models_registry.py    言語→モデルURL/高さ + ダウンロード（進捗付き）
  clipboard_watch.py    クリップボード画像の監視（Win+Shift+S連携）
  tts.py                オフライン読み上げ（pyttsx3 / SAPI5）
  translate.py          OpenAI互換ローカルLLMへの翻訳リクエスト
  tray.py               トレイメニュー（pystray）
  webview_ui.py         pywebviewのネイティブ窓管理（js_apiでフォルダ選択）
  config.py / paths.py  設定(config.json)とパス解決（dev/exe両対応）
  web/                  Flask: UIページ(setup/settings) + JSON API
    templates/  static/ 可愛いHTML/CSS/JS
```

## 開発実行

```bat
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python main.py
```

初回はセットアップ窓が開きます。言語を選び「ダウンロードして始める」でモデルを取得。
以降はトレイの **設定を開く** から設定窓を表示できます。

## exe化 と インストーラ

```bat
build.bat              :: dist\OCR_Transcribe\ を生成（約240MB, 起動高速化のためonedir）
build_installer.bat    :: Inno Setup 6 が必要。installer_out\OCR_Transcribe_Setup.exe を生成
```

インストーラは管理者権限不要で `%LocalAppData%\Programs\OCR_SCREEN_CAPTURE_TRANSCRIPTION`
にインストールします（スタートメニュー登録、任意でスタートアップ自動起動／デスクトップアイコン）。

## 翻訳（ローカルLLM）

[Ollama](https://ollama.com/) 等のOpenAI互換APIを起動し、設定UIの「翻訳」でエンドポイント
（既定 `http://localhost:11434/v1`）とモデル名・翻訳先言語を指定。LLM未起動時は翻訳のみ
スキップされ、OCRは通常どおり動作します。

## 補足

- 設定ファイル `config.json` とログ `ocr_tool.log` はexe（または`main.py`）と同じ場所に作成されます。
- pywebviewはWindowsの **Edge WebView2**（Windows 11標準搭載）を使用します。
- 使用ライブラリ: RapidOCR(onnxruntime) / pystray / pyttsx3 / pyperclip / pywin32 /
  requests / Flask / pywebview / PyInstaller。