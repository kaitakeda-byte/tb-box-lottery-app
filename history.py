"""BOX抽選履歴スプシ操作"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from googleapiclient.discovery import build

from auth import creds

HISTORY_SID = "1DqB7cg6Om4WA7ApF6GLVCVGLSBof0mr-7Ff20lB1jqs"
JST = timezone(timedelta(hours=9))


def _svc():
    return build("sheets", "v4", credentials=creds())


def load_past_winners() -> set[str]:
    """既当選者タブから@ハンドル一覧を取得"""
    svc = _svc()
    r = svc.spreadsheets().values().get(
        spreadsheetId=HISTORY_SID, range="既当選者!A2:A",
    ).execute()
    vals = r.get("values", [])
    return {row[0].strip().lstrip("@") for row in vals if row and row[0]}


def append_lottery(
    period_from: str,
    period_to: str,
    pool_size: int,
    clean_users: int,
    seed: str,
    winner_handle: str,
    winner_url: str,
    note: str = "",
):
    """抽選履歴に追記 + 既当選者にも自動追加"""
    svc = _svc()
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    today = datetime.now(JST).strftime("%Y-%m-%d")

    handle_clean = winner_handle.strip().lstrip("@")

    svc.spreadsheets().values().append(
        spreadsheetId=HISTORY_SID,
        range="抽選履歴!A:J",
        valueInputOption="USER_ENTERED",
        body={"values": [[
            period_from, period_to, now, pool_size, clean_users, seed,
            f"@{handle_clean}", winner_url, "未送信", note,
        ]]},
    ).execute()

    svc.spreadsheets().values().append(
        spreadsheetId=HISTORY_SID,
        range="既当選者!A:C",
        valueInputOption="USER_ENTERED",
        body={"values": [[handle_clean, today, f"{period_from}〜{period_to}期間 当選"]]},
    ).execute()


def mark_dm_sent(winner_handle: str):
    """直近の当選者行のDM送信状況を更新"""
    handle_clean = "@" + winner_handle.strip().lstrip("@")
    svc = _svc()
    r = svc.spreadsheets().values().get(
        spreadsheetId=HISTORY_SID, range="抽選履歴!A:J",
    ).execute()
    vals = r.get("values", [])
    # 一番下のマッチする行を更新
    for idx in range(len(vals) - 1, 0, -1):
        if len(vals[idx]) >= 7 and vals[idx][6] == handle_clean:
            row_num = idx + 1
            svc.spreadsheets().values().update(
                spreadsheetId=HISTORY_SID,
                range=f"抽選履歴!I{row_num}",
                valueInputOption="USER_ENTERED",
                body={"values": [["DM送信済"]]},
            ).execute()
            return row_num
    return None
