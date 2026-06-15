"""X DM 文面テンプレと deeplink 生成"""
from __future__ import annotations

import urllib.parse

DM_TEMPLATE = """突然のご連絡失礼いたします。
トレカバンク郵送買取（@torecabank_yuso）担当でございます。

この度は、X口コミボックスプレゼントキャンペーンにご応募いただき
誠にありがとうございます。
厳正なる抽選の結果、ご当選されましたことをご報告いたします🎉

賞品発送のお手続きのため、郵送買取ご利用時のお客様IDを
お伺いできますでしょうか。
お手数ではございますが、ご確認のうえご返信いただけますと幸いです。

何卒よろしくお願いいたします。"""


def build_dm_deeplink(recipient_handle: str, text: str | None = None) -> str:
    """X DM画面を文面プリセット付きで開くURLを生成

    https://x.com/messages/compose?recipient_id=&text=
    """
    text = text or DM_TEMPLATE
    handle = recipient_handle.strip().lstrip("@")
    params = {
        "recipient_screen_name": handle,
        "text": text,
    }
    return "https://x.com/messages/compose?" + urllib.parse.urlencode(params)
