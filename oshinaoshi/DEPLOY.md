# お直し管理アプリ — クラウド公開手順

スタッフが各自のスマホからURLで使えるよう公開する手順です。
**いまは無料の PythonAnywhere で公開します**（データも消えません）。
将来もっと安定させたくなったら、末尾の Render（有料）に移せます。

---

## ① PythonAnywhere で無料公開（今回これ）

### 1. アカウント作成
- https://www.pythonanywhere.com → 「Pricing & signup」→ **Beginner（無料）** で登録（カード不要）
- ユーザー名（例: `sarto`）を決める。URLは `https://ユーザー名.pythonanywhere.com` になる

### 2. コードを取得（Bashコンソール）
- ダッシュボード → 「Consoles」→「Bash」を開き、次を実行:
  ```
  git clone https://github.com/hotwaterhigh-crypto/x-auto.git
  pip install --user flask
  ```

### 3. Webアプリを作成
1. 「Web」タブ →「Add a new web app」→ Next
2. 「**Manual configuration**」を選ぶ →（最新の Python、例 3.10）→ Next → 完了

### 4. WSGI設定を貼り替え
1. 「Web」タブの中ほど **「WSGI configuration file」** のリンクを開く
2. 中身を全部消して、`oshinaoshi/pythonanywhere_wsgi.py` の内容を貼り付け
3. 次の3か所を自分のものに書き換えて保存:
   - `YOURNAME` → PythonAnywhereのユーザー名
   - `APP_PASSCODE` → スタッフ共有の合言葉（例: `sarto2026`）
   - `SECRET_KEY` → Claudeが渡したランダム文字列

### 5. 公開
- 「Web」タブの緑の **「Reload」** ボタンを押す
- `https://ユーザー名.pythonanywhere.com` を開く → 合言葉ログイン画面が出れば成功！
- スタッフに **URL** と **合言葉** を伝える

### 更新したいとき
- Bashコンソールで `cd x-auto && git pull` → 「Web」タブで「Reload」

### 注意
- 無料プランは3か月ごとに「まだ使ってますか？」の確認ボタンが出る（押すだけ）
- データは `oshinaoshi/data.db` に保存され、消えません。バックアップは `oshinaoshi/backups/`

---

## ② Render（あとで有料・月$7）に移す場合

リポジトリに `render.yaml` を用意済み。
1. https://render.com → GitHubでログイン
2. 「New +」→「Blueprint」→ リポジトリ `x-auto` を選ぶ → Apply
3. `oshinaoshi` サービス →「Environment」→ `APP_PASSCODE` に合言葉を設定
4. 数分でデプロイ完了 → URLをスタッフに共有

- 永続ディスク `/var/data` にデータ保存（消えない）
- コードを push すると自動で再デプロイ
