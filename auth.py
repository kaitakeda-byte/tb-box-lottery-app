"""Google OAuth credentials (X-egosearch refresh token を流用).

ローカル: X-egosearch/oauth_client.json + .env から読込
Streamlit Cloud: OAUTH_CLIENT_JSON / SHEETS_OAUTH_REFRESH_TOKEN を環境変数で受ける
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials

ROOT = Path(__file__).resolve().parent
for _env_p in [ROOT.parent / "X-egosearch" / ".env", ROOT / ".env"]:
    if _env_p.exists():
        load_dotenv(_env_p)
        break

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

_oauth_candidates = [
    ROOT.parent / "X-egosearch" / "oauth_client.json",
    ROOT / "oauth_client.json",
]


def _load_oauth_client() -> dict:
    """OAuth client config を取得。

    優先度:
      1. 環境変数 OAUTH_CLIENT_JSON (Streamlit Cloud Secrets想定)
      2. oauth_client.json ファイル (ローカル)
    """
    env_json = os.environ.get("OAUTH_CLIENT_JSON", "").strip()
    if env_json:
        return json.loads(env_json)["installed"]
    for p in _oauth_candidates:
        if p.exists():
            return json.loads(p.read_text())["installed"]
    raise FileNotFoundError(
        "oauth_client.json not found. Set OAUTH_CLIENT_JSON env var "
        "or place oauth_client.json in box_lottery_app/ or X-egosearch/"
    )


def creds() -> Credentials:
    inst = _load_oauth_client()
    return Credentials(
        token=None,
        refresh_token=os.environ["SHEETS_OAUTH_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=inst["client_id"],
        client_secret=inst["client_secret"],
        scopes=SCOPES,
    )
