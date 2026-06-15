# BOX抽選ツール (郵送買取口コミCP)

#トレカバンク郵送買取 投稿者からBOX当選者を抽選するStreamlit Web App。

## アクセス

- 本番URL: (デプロイ後に追記)
- パスワード: `box_lottery_app/.env` の `APP_PASSWORD`

## 使い方

1. 抽選対象期間を選択（前回抽選翌日〜今週末）
2. 「投稿を取得」→ SocialData APIで投稿を全件取得
3. フィルタ結果を確認（ハード除外/グレー/既当選者）
4. 「抽選する」→ クリーン投稿者プールから1名選出（seed記録）
5. 「履歴スプシに保存」→ [BOX抽選履歴](https://docs.google.com/spreadsheets/d/1DqB7cg6Om4WA7ApF6GLVCVGLSBof0mr-7Ff20lB1jqs/edit) に追記
6. 「DM画面を開く」→ X DM画面が文面プリセット済みで開く（手動送信）
7. 「DM送信済としてマーク」→ 履歴の送信状況を更新

## ローカル実行

```powershell
cd "G:\マイドライブ\project\Toreca Bank\box_lottery_app"
pip install -r requirements.txt
streamlit run app.py
```

ブラウザで http://localhost:8501 を開く。

## Cloud Runデプロイ

```powershell
cd "G:\マイドライブ\project\Toreca Bank\box_lottery_app"
.\deploy.ps1
```

初回は `APP_PASSWORD` が自動生成され `.env` に保存される。

## 設計

| ファイル | 役割 |
|---|---|
| app.py | Streamlit UI |
| fetcher.py | SocialData API取得 |
| classifier.py | HARD_NEG/SOFT_NEG/EMPTY/CLEAN 分類 |
| history.py | BOX抽選履歴スプシ読み書き |
| dm_template.py | DM文面 + X deeplink生成 |
| auth.py | Google OAuth (X-egosearch refresh token流用) |

## 依存

- X-egosearch/.env の `SHEETS_OAUTH_REFRESH_TOKEN`, `SOCIALDATA_API_KEY`
- X-egosearch/oauth_client.json
- 履歴スプシID: `1DqB7cg6Om4WA7ApF6GLVCVGLSBof0mr-7Ff20lB1jqs`

## 次フェーズ予定 (v2)

- X API直送信 (tb-kaitori-postアプリ流用)
- pay-per-use料金確認後実装
