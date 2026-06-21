"""TB Lottery Station

郵送買取口コミキャンペーンの当選者をX投稿から抽選するツール。
"""
from __future__ import annotations

import os
import random
import time
from datetime import date, timedelta

import streamlit as st

# Streamlit Cloud Secrets → 環境変数
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


st.set_page_config(
    page_title="TB Lottery Station",
    page_icon="▦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }

.stApp { background: #FAFBFC; }

.block-container {
    padding-top: 3rem;
    padding-bottom: 5rem;
    max-width: 880px;
}

html, body, [class*="css"], .stMarkdown, .stText {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
                 "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP",
                 Meiryo, sans-serif;
    color: #2D3748;
}

h1 { font-weight: 700; letter-spacing: -0.025em; color: #1A202C; font-size: 2rem; }
h2 { font-weight: 600; letter-spacing: -0.015em; color: #1A202C; font-size: 1.4rem; margin-top: 2rem; }
h3 { font-weight: 600; letter-spacing: -0.01em; color: #2D3748; font-size: 1.05rem; margin-top: 1.5rem; }

.stCaption, [data-testid="stCaptionContainer"] {
    color: #718096;
}

/* Primary button = brand teal */
.stButton > button[kind="primary"], .stLinkButton > a[kind="primary"] {
    background: #0E8C8F;
    color: #FFFFFF;
    border: 1px solid #0E8C8F;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 500;
    transition: background 0.15s;
    box-shadow: 0 1px 2px rgba(14,140,143,0.18);
}
.stButton > button[kind="primary"]:hover {
    background: #0A6F72;
    border-color: #0A6F72;
}

/* Secondary button = subtle dark */
.stButton > button:not([kind="primary"]) {
    background: #FFFFFF;
    color: #2D3748;
    border: 1px solid #CBD5E0;
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 500;
}
.stButton > button:not([kind="primary"]):hover {
    background: #F7FAFC;
    border-color: #A0AEC0;
}

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px 18px;
}
[data-testid="stMetricLabel"] {
    color: #718096;
    font-size: 0.78rem;
    font-weight: 500;
}
[data-testid="stMetricValue"] {
    color: #1A202C;
    font-weight: 700;
    font-size: 1.8rem;
}

hr { border: none; border-top: 1px solid #E2E8F0; margin: 2rem 0; }

[data-testid="stExpander"] {
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    background: #FFFFFF;
}

.stTextInput input, .stDateInput input, .stNumberInput input {
    border-radius: 10px;
    border: 1px solid #CBD5E0;
    background: #FFFFFF;
}

.stCode, code {
    background: #F7FAFC !important;
    border-radius: 8px;
    font-size: 0.85rem;
}

[data-testid="stAlert"] {
    border-radius: 10px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─── パスワード認証 ─────────────────────────────────────
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
if APP_PASSWORD:
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if not st.session_state.authed:
        st.title("TB Lottery Station")
        st.caption("郵送買取口コミキャンペーン 抽選管理")
        st.markdown("")
        pw = st.text_input("パスワード", type="password", label_visibility="collapsed", placeholder="パスワード")
        if st.button("入室", type="primary"):
            if pw == APP_PASSWORD:
                st.session_state.authed = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        st.stop()


# ─── Session state ─────────────────────────────────────
for key, default in [
    ("candidates", None),
    ("pool_result", None),
    ("winner", None),
    ("winner_seed", None),
    ("lottery_saved", False),
    ("winner_celebrated", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─── Header ────────────────────────────────────────────
st.title("TB Lottery Station")
st.caption("郵送買取口コミキャンペーン 抽選管理")

with st.expander("操作の流れ", expanded=False):
    st.markdown("""
1. 抽選対象期間を選択（前回抽選翌日から今週末まで）
2. 「投稿を取得」を押し、ハッシュタグ投稿を取得
3. 自動フィルタの結果を確認（ネガ言及・既当選者・空投稿は自動で外れる）
4. 「抽選」を押すと対象プールから1名選出
5. 「履歴に保存」で履歴シートへ記録
6. 「DMを開く」でX DM画面が文面プリセット済みで開く
7. 送信後に「DM送信済にする」で履歴を更新

履歴シート: [BOX抽選履歴_郵送買取CP](https://docs.google.com/spreadsheets/d/{}/edit)
    """.format(HISTORY_SID))

st.markdown("---")


# ─── Section 1: 期間 ───────────────────────────────────
st.markdown("### 対象期間")
today = date.today()
col1, col2 = st.columns(2)
with col1:
    start = st.date_input("開始日", value=today - timedelta(days=7))
with col2:
    end = st.date_input("終了日（含む）", value=today - timedelta(days=1))

if end < start:
    st.error("終了日が開始日より前です")
    st.stop()

st.markdown("")
if st.button("投稿を取得", type="primary", use_container_width=True):
    st.session_state.candidates = None
    st.session_state.pool_result = None
    st.session_state.winner = None
    st.session_state.lottery_saved = False
    st.session_state.winner_celebrated = False

    progress_box = st.empty()
    log_lines: list[str] = []

    def progress(msg):
        log_lines.append(msg)
        progress_box.code("\n".join(log_lines[-10:]))

    with st.spinner("取得中"):
        try:
            rows = fetch_range(start, end, progress=progress)
            past_winners = load_past_winners()
            progress(f"既当選者 {len(past_winners)}名を除外: {', '.join(sorted(past_winners))}")
            st.session_state.candidates = rows
            st.session_state.pool_result = split_pool(rows, past_winners)
        except Exception as e:
            st.error(f"取得失敗: {e}")


# ─── Section 2: 取得結果 ───────────────────────────────
if st.session_state.pool_result:
    pr = st.session_state.pool_result
    clean_users = pr["clean_users"]

    st.markdown("---")
    st.markdown("### 取得結果")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("取得投稿", len(st.session_state.candidates))
    c2.metric("対象者", len(clean_users))
    c3.metric("グレー", len(pr["gray"]))
    c4.metric("除外", len(pr["excluded"]) + len(pr["past_winner_posts"]))

    with st.expander(f"対象プール {len(clean_users)}名", expanded=True):
        for sn in sorted(clean_users.keys()):
            for r in clean_users[sn]:
                st.markdown(
                    f"**@{sn}** ・ {r['created_at'][:10]} ・ FW {r['user_followers']} ・ "
                    f"[投稿を開く]({r['url']})  \n"
                    f"<span style='color:#718096;font-size:0.88rem'>{r['text'][:90]}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("")

    if pr["past_winner_posts"]:
        with st.expander(f"既当選者 {len(pr['past_winner_posts'])}件"):
            for r in pr["past_winner_posts"]:
                st.markdown(f"**@{r['screen_name']}** ・ {r['created_at'][:10]}")
                st.caption(r["text"][:90])

    if pr["gray"]:
        with st.expander(f"グレー {len(pr['gray'])}件"):
            for r in pr["gray"]:
                st.markdown(f"**@{r['screen_name']}** ・ {r['created_at'][:10]}")
                st.caption(r["text"][:90])

    if pr["excluded"]:
        with st.expander(f"除外 {len(pr['excluded'])}件"):
            for c, r in pr["excluded"]:
                st.markdown(f"**@{r['screen_name']}** ・ {r['created_at'][:10]}")
                st.caption(r["text"][:90])

    # ─── Section 3: 抽選 ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 抽選")

    if len(clean_users) == 0:
        st.warning("対象者がいません")
    else:
        col_a, col_b = st.columns([3, 1])
        with col_a:
            seed_input = st.text_input(
                "seed", value="", placeholder="空欄でランダム",
                label_visibility="collapsed",
            )
        with col_b:
            draw_clicked = st.button("抽選", type="primary", use_container_width=True)

        if draw_clicked:
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
            st.session_state.winner_celebrated = False


# ─── Section 4: 結果 ───────────────────────────────────
if st.session_state.winner:
    winner = st.session_state.winner
    seed = st.session_state.winner_seed
    pr = st.session_state.pool_result
    winner_posts = pr["clean_users"].get(winner, [])
    primary_post = winner_posts[0] if winner_posts else {}

    if not st.session_state.winner_celebrated:
        st.balloons()
        st.session_state.winner_celebrated = True

    st.markdown("---")
    st.markdown("### 結果")

    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:16px;
                    padding:36px 24px;text-align:center;margin:18px 0;
                    box-shadow:0 6px 18px rgba(14,140,143,0.08);">
            <div style="color:#A0AEC0;font-size:0.72rem;letter-spacing:0.18em;
                        font-weight:600;margin-bottom:10px;">WINNER</div>
            <div style="font-size:2.2rem;font-weight:700;color:#0E8C8F;
                        letter-spacing:-0.02em;">@{winner}</div>
            <div style="color:#A0AEC0;font-size:0.78rem;margin-top:14px;
                        font-family:monospace;">seed: {seed}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if winner_posts:
        with st.expander("当選対象の投稿", expanded=True):
            for r in winner_posts:
                st.markdown(
                    f"**{r['created_at'][:10]}** ・ FW {r['user_followers']} ・ "
                    f"[投稿を開く]({r['url']})  \n"
                    f"{r['text'][:200]}"
                )
                st.markdown("")

    st.markdown("---")
    st.markdown("### 確定とDM送信")
    col_save, col_dm = st.columns(2)

    with col_save:
        if not st.session_state.lottery_saved:
            if st.button("履歴に保存", type="primary", use_container_width=True):
                try:
                    append_lottery(
                        period_from=str(start),
                        period_to=str(end),
                        pool_size=len(st.session_state.candidates),
                        clean_users=len(pr["clean_users"]),
                        seed=str(seed),
                        winner_handle=winner,
                        winner_url=primary_post.get("url", ""),
                    )
                    st.session_state.lottery_saved = True
                    st.success("保存しました")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失敗: {e}")
        else:
            st.success("保存済")

    with col_dm:
        dm_url = build_dm_deeplink(winner)
        st.link_button("DMを開く", dm_url, type="primary", use_container_width=True)

    with st.expander("DM文面を表示"):
        st.code(DM_TEMPLATE, language="text")

    if st.session_state.lottery_saved:
        st.markdown("")
        if st.button("DM送信済にする", use_container_width=True):
            try:
                row_num = mark_dm_sent(winner)
                if row_num:
                    st.success("更新しました")
                else:
                    st.warning("該当行が見つかりません")
            except Exception as e:
                st.error(f"更新失敗: {e}")


# ─── Footer ────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align:center;color:#A0AEC0;font-size:0.78rem;padding:20px 0;'>
        履歴シート ・
        <a href='https://docs.google.com/spreadsheets/d/{HISTORY_SID}/edit'
           style='color:#718096;text-decoration:none;border-bottom:1px solid #CBD5E0;'>
            BOX抽選履歴_郵送買取CP
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
