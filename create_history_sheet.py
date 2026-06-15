"""BOX抽選履歴スプシ新規作成 + 過去2回分シード投入"""
from googleapiclient.discovery import build

from auth import creds


SEED_HISTORY = [
    # 期間From, 期間To, 抽選日時(JST), 母集団件数, クリーン投稿者数, seed, 当選@, 当選URL, DM送信状況, 備考
    ["2026-05-03", "2026-05-14", "(履歴遡及記録)", 68, "", "", "@keeento777", "", "DM送信済", "初回当選者"],
    ["2026-05-23", "2026-06-06", "2026-06-07", 44, 24, "1780898410", "@yuyuyutatata525", "https://x.com/yuyuyutatata525/status/2059904860624208005", "DM送信済", ""],
    ["2026-06-07", "2026-06-14", "2026-06-15", 27, 15, "1781501008", "@YK012500", "https://x.com/YK012500/status/2064862371278196758", "未送信", ""],
]


def main():
    svc = build("sheets", "v4", credentials=creds())
    new = svc.spreadsheets().create(body={
        "properties": {"title": "BOX抽選履歴_郵送買取CP"},
        "sheets": [
            {"properties": {"title": "抽選履歴", "gridProperties": {"frozenRowCount": 1}}},
            {"properties": {"title": "既当選者", "gridProperties": {"frozenRowCount": 1}}},
            {"properties": {"title": "_README"}},
        ],
    }, fields="spreadsheetId,spreadsheetUrl").execute()
    sid = new["spreadsheetId"]
    url = new["spreadsheetUrl"]
    print(f"スプシID : {sid}")
    print(f"URL      : {url}")

    svc.spreadsheets().values().batchUpdate(spreadsheetId=sid, body={
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": "'抽選履歴'!A1", "values": [[
                "期間From", "期間To", "抽選日時(JST)", "母集団件数",
                "クリーン投稿者数", "seed", "当選@ハンドル", "当選投稿URL",
                "DM送信状況", "備考",
            ]] + SEED_HISTORY},
            {"range": "'既当選者'!A1", "values": [
                ["@ハンドル", "初回当選日", "備考"],
                ["keeento777", "2026-05-XX", "初回当選者 (履歴遡及)"],
                ["yuyuyutatata525", "2026-06-07", "5/23-6/6期間 当選"],
                ["YK012500", "2026-06-15", "6/7-6/14期間 当選"],
            ]},
            {"range": "'_README'!A1", "values": [
                ["■ BOX抽選履歴 (郵送買取口コミCP)"],
                [""],
                ["【概要】"],
                ["・ 抽選履歴タブ: 期間ごとの抽選結果ログ"],
                ["・ 既当選者タブ: 過去当選者のハンドル一覧 (Web Appが自動参照→次回プールから除外)"],
                [""],
                ["【Web App URL】"],
                ["・ (デプロイ後追記)"],
                [""],
                ["【運用】"],
                ["・ Web Appで抽選確定するとここに自動追記される"],
                ["・ 手動編集する場合は @ハンドルの先頭@は付けず ハンドルのみ記入"],
            ]},
        ],
    }).execute()

    print()
    print("OK: history spreadsheet created with seed data")


if __name__ == "__main__":
    main()
