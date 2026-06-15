"""BOX抽選 Web App (Streamlit)

郵送買取口コミCPの当選者をX投稿から抽選するツール。

機能:
1. 期間指定 → SocialData APIで #トレカバンク郵送買取 投稿を全件取得
2. 既当選者除外 + ネガ言及フィルタ + 空投稿除外 → クリーンプール表示
3. seed記録付き抽選 → 当選者表示
4. X DM画面deeplink生成 → 文面プリセット済みで開く
5. 履歴スプシ自動追記 + 既当選者リスト自動更新
"""
from __future__ import annotations

import os
import random
import time
from datetime import date, timedelta

import streamlit as st

# Streamlit Cloud Secrets → 環境変数 へ反映 (auth/fetcherがos.environを参照するため)
try:
    for k, v in st.secrets.items():
        if isinstance(v, str):
            os.environ.setdefault(k, v)
except Exception:
    pass

from classifier import split_pool
from dm_template import DM_TEMPLATE, build_dm_deeplink
from fetcher import fetch_range
from history import HISTORY_SID, append_lottery, load_past_winners, mark_dm_sent


st.set_page_config(page_title="BOX抽選ツール", page_icon="🎁", layout="wide")

# 簡易パスワード認証 (環境変数 APP_PASSWORD 設定時のみ有効)
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
if APP_PASSWORD:
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if not st.session_state.authed:
        st.title("🔒 BOX抽選ツール")
        pw = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pw == APP_PASSWORD:
                st.session_state.authed = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        st.stop()

st.title("🎁 BOX抽選ツール")
st.caption("郵送買取口コミCP - 週次BOX当選者を #トレカバンク郵送買取 投稿から抽選")

with st.expander("📖 使い方", expanded=False):
    st.markdown("""
    1. 抽選対象期間（前回抽選翌日〜今週末など）を選択
    2. **「投稿を取得」**ボタン → SocialData APIで#トレカバンク郵送買取を全件取得
    3. フィルタ結果（ネガ言及/既当選者/空投稿の除外）を確認
    4. **「抽選する」**ボタン → クリーン投稿者プールから1名ランダム選出
    5. **「DM画面を開く」**ボタン → 文面プリセット済みのX DM画面が開く
    6. DM送信後に **「DM送信済としてマーク」**ボタンで履歴更新

    履歴スプシ: [BOX抽選履歴]({})
    """.format(f"https://docs.google.com/spreadsheets/d/{HISTORY_SID}/edit"))


# Session state init
if "candidates" not in st.session_state:
    st.session_state.candidates = None
if "pool_result" not in st.session_state:
    st.session_state.pool_result = None
if "winner" not in st.session_state:
    st.session_state.winner = None
if "winner_seed" not in st.session_state:
    st.session_state.winner_seed = None
if "lottery_saved" not in st.session_state:
    st.session_state.lottery_saved = False

# 期間指定
st.subheader("Step 1. 抽選対象期間を指定")
col1, col2 = st.columns(2)
today = date.today()
default_start = today - timedelta(days=7)
with col1:
    start = st.date_input("期間開始 (From)", value=default_start)
with col2:
    end = st.date_input("期間終了 (To, 含む)", value=today - timedelta(days=1))

if end < start:
    st.error("期間Toが期間Fromより前です")
    st.stop()

# 取得ボタン
if st.button("🔍 投稿を取得", type="primary"):
    st.session_state.candidates = None
    st.session_state.pool_result = None
    st.session_state.winner = None
    st.session_state.lottery_saved = False
    progress_box = st.empty()
    log_lines: list[str] = []

    def progress(msg):
        log_lines.append(msg)
        progress_box.code("\n".join(log_lines))

    with st.spinner("SocialData APIから取得中..."):
        try:
            rows = fetch_range(start, end, progress=progress)
            past_winners = load_past_winners()
            progress(f"既当選者: {len(past_winners)}名 ({', '.join(sorted(past_winners))})")
            pool_result = split_pool(rows, past_winners)
            st.session_state.candidates = rows
            st.session_state.pool_result = pool_result
            st.success(f"取得完了: {len(rows)}件")
        except Exception as e:
            st.error(f"取得失敗: {e}")

# プール表示
if st.session_state.pool_result:
    pr = st.session_state.pool_result
    clean_users = pr["clean_users"]
    excluded = pr["excluded"]
    gray = pr["gray"]
    past_winner_posts = pr["past_winner_posts"]

    st.divider()
    st.subheader("Step 2. フィルタ結果")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("取得投稿", len(st.session_state.candidates))
    m2.metric("✅ クリーン投稿者", len(clean_users))
    m3.metric("⚠️ グレー除外", len(gray))
    m4.metric("❌ ハード除外", len(excluded) + len(past_winner_posts))

    with st.expander(f"✅ クリーン投稿者プール {len(clean_users)}名 (抽選対象)", expanded=True):
        for sn in sorted(clean_users.keys()):
            posts = clean_users[sn]
            for r in posts:
                st.markdown(
                    f"- **@{sn}** ({r['created_at'][:10]}, FW:{r['user_followers']}) "
                    f"[投稿]({r['url']}): {r['text'][:80]}..."
                )

    if past_winner_posts:
        with st.expander(f"🚫 既当選者投稿 (除外) {len(past_winner_posts)}件"):
            for r in past_winner_posts:
                st.markdown(f"- **@{r['screen_name']}** ({r['created_at'][:10]}): {r['text'][:80]}")

    if gray:
        with st.expander(f"⚠️ グレー(部分ネガ言及・除外) {len(gray)}件"):
            for r in gray:
                st.markdown(f"- **@{r['screen_name']}** ({r['created_at'][:10]}): {r['text'][:80]}")

    if excluded:
        with st.expander(f"❌ ハード除外 (ネガ/空) {len(excluded)}件"):
            for c, r in excluded:
                st.markdown(f"- [{c}] **@{r['screen_name']}** ({r['created_at'][:10]}): {r['text'][:80]}")

    # 抽選
    st.divider()
    st.subheader("Step 3. 抽選実行")

    if len(clean_users) == 0:
        st.warning("クリーン投稿者がいません")
    else:
        col_a, col_b = st.columns([3, 1])
        with col_a:
            seed_input = st.text_input("seed (空欄でランダム生成)", value="")
        with col_b:
            if st.button("🎲 抽選する", type="primary"):
                if seed_input.strip():
                    try:
                        seed = int(seed_input.strip())
                    except ValueError:
                        seed = hash(seed_input.strip())
                else:
                    seed = int(time.time())
                rng = random.Random(seed)
                pool = sorted(clean_users.keys())
                winner = rng.choice(pool)
                st.session_state.winner = winner
                st.session_state.winner_seed = seed
                st.session_state.lottery_saved = False

# 当選者表示
if st.session_state.winner:
    winner = st.session_state.winner
    seed = st.session_state.winner_seed
    pr = st.session_state.pool_result
    winner_posts = pr["clean_users"].get(winner, [])
    primary_post = winner_posts[0] if winner_posts else {}

    st.divider()
    st.subheader("🏆 当選者")
    st.success(f"### @{winner}")
    st.code(f"seed: {seed}", language="text")

    if winner_posts:
        st.markdown("**当選対象投稿:**")
        for r in winner_posts:
            st.markdown(
                f"- [{r['created_at'][:10]} | FW:{r['user_followers']}]({r['url']})  \n"
                f"  {r['text'][:200]}"
            )

    # 履歴保存
    st.divider()
    st.subheader("Step 4. 履歴保存 & DM送信")

    col_save, col_dm = st.columns(2)

    with col_save:
        if not st.session_state.lottery_saved:
            if st.button("💾 抽選結果を履歴スプシに保存", type="primary"):
                try:
                    append_lottery(
                        period_from=str(start),
                        period_to=str(end),
                        pool_size=len(st.session_state.candidates),
                        clean_users=len(pr["clean_users"]),
                        seed=str(seed),
                        winner_handle=winner,
                        winner_url=primary_post.get("url", ""),
                        note="",
                    )
                    st.session_state.lottery_saved = True
                    st.success("履歴保存完了")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失敗: {e}")
        else:
            st.success("✅ 履歴保存済")

    with col_dm:
        dm_url = build_dm_deeplink(winner)
        st.link_button("✉️ DM画面を開く (文面プリセット済)", dm_url, type="primary")

    with st.expander("DM文面プレビュー"):
        st.code(DM_TEMPLATE, language="text")

    if st.session_state.lottery_saved:
        if st.button("✅ DM送信済としてマーク"):
            try:
                row_num = mark_dm_sent(winner)
                if row_num:
                    st.success(f"履歴スプシのDM送信状況を更新 (Row {row_num})")
                else:
                    st.warning("該当行が見つかりませんでした")
            except Exception as e:
                st.error(f"更新失敗: {e}")

st.divider()
st.caption(f"履歴スプシ: [{HISTORY_SID}](https://docs.google.com/spreadsheets/d/{HISTORY_SID}/edit)")
