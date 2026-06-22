# PythonAnywhere 用 WSGI 設定のサンプル
# ─────────────────────────────────────────────
# 使い方:
#   PythonAnywhere の「Web」タブ → WSGI configuration file を開き、
#   中身をすべて消して、この内容を貼り付ける。
#   下の YOURNAME / 合言葉 / SECRET_KEY を自分のものに書き換える。
# ─────────────────────────────────────────────
import os
import sys

# プロジェクトの場所（YOURNAME を PythonAnywhere のユーザー名に）
project_path = "/home/YOURNAME/x-auto/oshinaoshi"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# スタッフ共有の合言葉（ここを好きな言葉に）
os.environ["APP_PASSCODE"] = "ここに合言葉"
# ログイン用のランダム鍵（Claudeが生成したものを貼る）
os.environ["SECRET_KEY"] = "ここにSECRET_KEY"
# DATA_DIR は未設定でOK（oshinaoshi フォルダに保存され、消えません）

from app import app as application
