"""NerdLore: Streamlit app. Run with:  streamlit run app.py"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from nerdlore import analysis, charts, demo, local_store
from nerdlore.data import DataError, load_export
from nerdlore.youtube import YouTubeError, fetch_views, search_other_uploads

YT_TERMS = "https://www.youtube.com/t/terms"
GOOGLE_PRIVACY = "https://policies.google.com/privacy"
HACKERTUBE = "https://hackertube.org"
HN_DATASET = "https://huggingface.co/datasets/open-index/hacker-news"
ODC_BY = "https://opendatacommons.org/licenses/by/1-0/"
KEY_HELP = "https://developers.google.com/youtube/v3/getting-started"

st.set_page_config(page_title="NerdLore", page_icon="💎", layout="wide")
st.html("""<style>
/* Streamlit hides scrollbars until hover; keep them visible so people can see there is more to scroll. */
* { scrollbar-color: rgba(128, 128, 128, 0.6) transparent !important; }
*:hover { scrollbar-color: rgba(128, 128, 128, 0.9) transparent !important; }
/* Less empty space at the top of every page and of the sidebar. */
[data-testid="stMainBlockContainer"] { padding-top: 1.1rem !important; padding-bottom: 1.2rem !important; }
[data-testid="stHeader"] { background: transparent; }  /* the toolbar strip no longer hides the page header */
/* That strip covers the top of the page. Let clicks pass through it to the NerdLore header (Home, Try the demo,
   the title and logo); only Streamlit's own buttons and links in it (Deploy, the menu) still catch clicks. */
[data-testid="stHeader"], [data-testid="stHeader"] * { pointer-events: none; }
[data-testid="stHeader"] button, [data-testid="stHeader"] a, [data-testid="stHeader"] [role="button"] { pointer-events: auto; }
[data-testid="stSidebarHeader"] { height: 2rem; padding: 0.5rem 1rem 0; }
[data-testid="stSidebarUserContent"] { padding-top: 0 !important; }
[data-testid="stSidebarUserContent"] h1 { padding-top: 0; }
/* Header */
.htg-head { display: flex; align-items: center; gap: 14px; margin-right: 7rem; }
.htg-logo { width: 42px; height: 42px; flex: none; display: grid; place-items: center; border-radius: 11px; font-size: 22px;
  background: linear-gradient(135deg, rgba(255,122,61,.22), rgba(167,139,250,.22), rgba(61,214,255,.22));
  border: 1px solid rgba(167,139,250,.4); box-shadow: 0 0 22px -8px rgba(167,139,250,.8); }
.htg-title { font-size: 1.45rem; font-weight: 700; line-height: 1.15; letter-spacing: -.01em; }
.htg-sub { font-size: .92rem; opacity: .68; }
/* Section headers inside tabs */
.htg-eyebrow { font: 600 .68rem/1 ui-monospace, "Cascadia Mono", Consolas, monospace; letter-spacing: .14em;
  text-transform: uppercase; color: #a78bfa; }
.htg-h { font-size: 1.32rem; font-weight: 700; margin: .3rem 0 .15rem; letter-spacing: -.01em; }
.htg-sec p { margin: 0; opacity: .72; font-size: .95rem; }
.htg-rule { margin: .2rem 0 .3rem; padding: .55rem .8rem; border-left: 3px solid #a78bfa; border-radius: 0 8px 8px 0;
  background: rgba(167,139,250,.08); font-size: .9rem; }
/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 2px; }
.stTabs [data-baseweb="tab"] { height: 2.4rem; padding: 0 .95rem; border-radius: 8px 8px 0 0; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { background: rgba(255,122,61,.10); }
.stTabs [data-baseweb="tab-panel"] { padding-top: .9rem; }
/* The interactive pages size their own container to fit. When Streamlit reuses that container for
   something else (e.g. after leaving the home page), drop the leftover height so no blank gap is left. */
[data-testid="stElementContainer"]:not(:has(iframe)) { height: auto !important; }
/* Header: the logo and the NerdLore title are buttons that open the home page */
.st-key-home_logo button { width: 42px; height: 42px; min-height: 42px; padding: 0; border-radius: 11px;
  background: linear-gradient(135deg, rgba(255,122,61,.22), rgba(167,139,250,.22), rgba(61,214,255,.22));
  border: 1px solid rgba(167,139,250,.4); box-shadow: 0 0 22px -8px rgba(167,139,250,.8); }
.st-key-home_logo button p { font-size: 22px; line-height: 1; }
.st-key-home_logo button:hover { border-color: rgba(255,122,61,.8); }
.st-key-home_title { margin-bottom: -.95rem; }
.st-key-home_title button { padding: 0; min-height: 0; height: auto; }
.st-key-home_title button p { font-size: 1.45rem; font-weight: 700; line-height: 1.15; letter-spacing: -.01em; }
.st-key-home_title button:hover p { color: #ff7a3d; }
.st-key-home_side button { padding: 0; min-height: 0; justify-content: flex-start; }
.st-key-home_side button p { font-size: 1.6rem; font-weight: 700; letter-spacing: -.01em; }
.st-key-home_side button:hover p { color: #ff7a3d; }
/* Demo mode markers: a pill in the header and a badge that stays in the corner while you scroll */
.htg-demo-pill { display: inline-flex; align-items: center; gap: 6px; margin-left: 10px; padding: 2px 10px;
  border-radius: 999px; border: 1px solid rgba(255,122,61,.7); background: rgba(255,122,61,.16); color: #ff9a66;
  font: 700 .68rem/1.6 ui-monospace, "Cascadia Mono", Consolas, monospace; letter-spacing: .1em; vertical-align: middle;
  opacity: 1; }
.htg-demo-pill i, .htg-demo-float i { width: 7px; height: 7px; border-radius: 50%; background: #ff7a3d;
  animation: htgBlink 1.6s ease-in-out infinite; }
.htg-demo-float { position: fixed; right: 18px; bottom: 18px; z-index: 1000; display: flex; align-items: center; gap: 8px;
  padding: 9px 14px; border-radius: 12px; border: 1px solid rgba(255,122,61,.8); background: rgba(30,18,12,.92);
  color: #ffb08a; font: 700 .78rem/1.3 ui-monospace, "Cascadia Mono", Consolas, monospace; letter-spacing: .06em;
  box-shadow: 0 8px 28px -10px rgba(255,122,61,.8); pointer-events: none; }
@keyframes htgBlink { 0%, 100% { opacity: 1; } 50% { opacity: .25; } }
@media (prefers-reduced-motion: reduce) { .htg-demo-pill i, .htg-demo-float i { animation: none; } }
/* "Try the demo": bigger and gently animated so first-time visitors spot it */
.st-key-demo_main button { min-height: 4.3rem; border: 0 !important; border-radius: 14px; color: #fff !important;
  background: linear-gradient(110deg, #ff7a3d 0%, #ff8f52 45%, #a78bfa 100%) !important;
  position: relative; overflow: hidden; transition: transform .15s ease;
  animation: htgPulse 2.4s ease-in-out infinite; }
.st-key-demo_main button p { font-size: 1.32rem; font-weight: 800; letter-spacing: .01em; }
.st-key-demo_main button span[data-testid="stIconMaterial"] { font-size: 1.5rem; }
.st-key-demo_main button::after { content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(100deg, transparent 30%, rgba(255,255,255,.38) 50%, transparent 70%);
  transform: translateX(-130%); animation: htgShine 3.4s ease-in-out infinite; }
.st-key-demo_main button:hover { transform: translateY(-2px) scale(1.02); }
.st-key-demo_side button, .st-key-demo_top button { border-color: rgba(255,122,61,.75) !important;
  animation: htgPulseSoft 2.8s ease-in-out infinite; }
.st-key-demo_top button p { color: #ffb08a; font-weight: 700; }
/* While the demo is on: bright, pulsing "DEMO MODE · Exit" buttons so nobody mistakes the numbers for real ones */
.st-key-demo_exit_top button, .st-key-demo_exit_side button { border: 0 !important; color: #fff !important;
  background: linear-gradient(110deg, #ff7a3d 0%, #ff8f52 45%, #a78bfa 100%) !important;
  animation: htgPulse 2.4s ease-in-out infinite; }
.st-key-demo_exit_top button p, .st-key-demo_exit_side button p { font-weight: 800; letter-spacing: .04em; }
@keyframes htgPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255,122,61,.55), 0 8px 24px -10px rgba(255,122,61,.8); }
  50% { box-shadow: 0 0 0 12px rgba(255,122,61,0), 0 10px 34px -8px rgba(167,139,250,.85); } }
@keyframes htgShine { 0%, 55% { transform: translateX(-130%); } 100% { transform: translateX(130%); } }
@keyframes htgPulseSoft { 0%, 100% { box-shadow: 0 0 0 0 rgba(255,122,61,.45); } 50% { box-shadow: 0 0 0 6px rgba(255,122,61,0); } }
@media (prefers-reduced-motion: reduce) {
  .st-key-demo_main button, .st-key-demo_main button::after, .st-key-demo_side button, .st-key-demo_top button,
  .st-key-demo_exit_top button, .st-key-demo_exit_side button { animation: none; } }
/* Small print */
.htg-fine { font-size: .74rem; line-height: 1.5; opacity: .58; }
.htg-fine a { color: inherit; }
</style>""")

PRIVACY = (Path(__file__).parent / "PRIVACY.md").read_text(encoding="utf-8").removeprefix("### Privacy notice").strip()


@st.dialog("Privacy notice", width="large")
def privacy_dialog() -> None:
    st.markdown(PRIVACY)


def section(eyebrow: str, title: str, text: str = "") -> None:
    """A compact tab heading: small label, title, one line of explanation (HTML allowed)."""
    st.html(f'<div class="htg-sec"><div class="htg-eyebrow">{eyebrow}</div><div class="htg-h">{title}</div>'
            + (f"<p>{text}</p>" if text else "") + "</div>")


def footer(demo_mode: bool = False) -> None:
    # YouTube API policy III.A.2: say that use means agreeing to YouTube's terms; privacy notice one click away.
    st.divider()
    fine, button = st.columns([7, 1], vertical_alignment="center")
    fine.html(
        f'<div class="htg-fine">Uses YouTube API Services: by using this app you agree to the '
        f'<a href="{YT_TERMS}" target="_blank">YouTube Terms of Service</a> · '
        f'<a href="{GOOGLE_PRIVACY}" target="_blank">Google Privacy Policy</a>. Unofficial; not affiliated with '
        f'HackerTube, Hacker News, Y Combinator, YouTube or Google. Video list, HN recommender counts and labels: '
        f'<a href="{HACKERTUBE}" target="_blank">HackerTube</a> export of the '
        f'<a href="{HN_DATASET}" target="_blank">open-index/hacker-news</a> dataset (Hacker News data by Y Combinator), '
        f'<a href="{ODC_BY}" target="_blank">ODC-By 1.0</a>; labels were written by an LLM. View counts and upload '
        f'dates come from the YouTube Data API, shown exactly as YouTube returns them.'
        + (' <b>Demo mode is on: the view counts and upload dates shown are made up.</b>' if demo_mode else '')
        + '</div>')
    if button.button("Privacy notice", type="tertiary", icon=":material/shield:", key="privacy_footer"):
        privacy_dialog()


def go_home() -> None:
    """A fresh start: the start page with the big Try the demo button, its animation replayed, scrolled to the top.

    A running demo ends (its numbers are made up and cost nothing to make again). Real results are kept, and come
    back from this computer straight away, one click from the start page.
    """
    if st.session_state.get("demo"):
        for k in ("stats", "demo", "demo_source", "ds", "filters", "dupes"):
            st.session_state.pop(k, None)
    st.session_state["home"] = True
    st.session_state["home_visit"] = st.session_state.get("home_visit", 0) + 1


def leave_home() -> None:
    st.session_state["home"] = False


# ---------- sidebar: inputs ----------
st.sidebar.button("💎 NerdLore", key="home_side", type="tertiary", on_click=go_home, help="Home")
st.sidebar.caption("Built on HackerTube's public data")

# Saving to disk only when the app is opened on this computer, so a hosted copy never shares one person's key.
on_this_computer = urlparse(st.context.url or "").hostname in ("localhost", "127.0.0.1", "::1")

st.sidebar.link_button("Get the zip from hackertube.org", f"{HACKERTUBE}/data", icon=":material/download:",
                       width="stretch")
upload = st.sidebar.file_uploader("Upload hackertube-data.zip", type=["zip"])
if on_this_computer:
    if upload is not None and st.session_state.get("saved_upload") != upload.file_id:
        local_store.save_zip(upload.getvalue())
        st.session_state["saved_upload"] = upload.file_id
    elif upload is None and local_store.has_zip():
        st.sidebar.caption("Using the zip you uploaded last time. Upload a new one to replace it.")



@st.cache_data(show_spinner=False, max_entries=1)
def saved_dataset(mtime: float):
    # HackerTube's public data only. Keyed on the file's modified time, so a new upload reloads it.
    return load_export(local_store.load_zip())


def shown_time(when: datetime) -> str:
    return when.strftime("%d %b %Y, %H:%M UTC")


# After a refresh, bring back the last run (view counts are kept for at most 30 days).
if on_this_computer and "stats" not in st.session_state and local_store.has_zip():
    saved_views = local_store.load_views()
    if saved_views:
        stats, filters, fetched = saved_views
        try:
            st.session_state.update(ds=saved_dataset(local_store.zip_mtime()), stats=stats, filters=filters,
                                    fetched_at=shown_time(fetched),
                                    views_expire=(fetched + local_store.MAX_VIEWS_AGE).strftime("%d %b %Y"),
                                    types=list(filters[0]), min_recs=filters[1], hide_news=filters[2])
        except DataError:
            pass

if "api_key" not in st.session_state:
    st.session_state["api_key"] = local_store.load_key() if on_this_computer else ""


def save_key() -> None:
    local_store.save_key(st.session_state["api_key"])
    st.toast("Key saved on this computer.")


def forget_key() -> None:
    local_store.forget_key()
    st.session_state["api_key"] = ""
    st.toast("Key deleted from this computer.")


api_key = st.sidebar.text_input("Your YouTube API key", type="password", key="api_key",
                                help=f"Don't know how to get one? [See Google's guide]({KEY_HELP}).\n\n"
                                     "Sent only to YouTube. Press **Save key** to keep it on this computer "
                                     "between visits, and **Forget key** to delete it.")
if on_this_computer:
    key_saved = bool(local_store.load_key())
    left, right = st.sidebar.columns(2)
    left.button("Save key", width="stretch", on_click=save_key, disabled=not api_key)
    right.button("Forget key", width="stretch", on_click=forget_key, disabled=not (key_saved or api_key))
    st.sidebar.caption("Key saved on this computer." if key_saved else "Key not saved: gone when you refresh.")
st.sidebar.caption(f"Free to create; restrict it to YouTube Data API v3. [How to get one]({KEY_HELP})")

st.sidebar.subheader("What to compare")
all_types = ["talk", "lecture", "explainer", "demo", "documentary", "interview", "tutorial", "course",
             "podcast", "commentary", "comedy", "news", "music", "other"]
st.session_state.setdefault("types", list(analysis.TALK_TYPES))
st.session_state.setdefault("min_recs", 5)
st.session_state.setdefault("hide_news", True)
types = st.sidebar.multiselect("Video types", all_types, key="types",
                               help="Compare like with like: talks with talks, not with music videos.")
min_recs = st.sidebar.slider("At least this many HN recommenders", 1, 20, key="min_recs")
hide_news = st.sidebar.checkbox("Hide videos that only mattered for one news event", key="hide_news")
run = st.sidebar.button("Run analysis", type="primary", width="stretch")
in_demo_now = bool(st.session_state.get("demo")) and "stats" in st.session_state
try_demo = False
if in_demo_now:
    st.sidebar.button("Demo mode is on · Exit demo", type="primary", width="stretch", icon=":material/logout:",
                      key="demo_exit_side", on_click=go_home,
                      help="Leave the demo and go back to the start page. The made-up numbers are thrown away.")
else:
    try_demo = st.sidebar.button("Try the demo (no key needed)", width="stretch", icon=":material/science:",
                                 key="demo_side",
                                 help="Every page with made-up view counts, so you can look around before you get "
                                      "a key. Uses your uploaded zip, or a small built-in sample. Nothing is saved.")
if st.sidebar.button("Forget YouTube data", width="stretch"):
    for k in ("stats", "fetched_at", "views_expire", "dupes", "demo"):
        st.session_state.pop(k, None)
    local_store.forget_views()
    st.sidebar.success("YouTube data deleted from this session and this computer.")
status_slot = st.sidebar.empty()  # filled in once we know whether there are view counts


def load_dataset():
    if upload is not None:
        return load_export(upload.getvalue())
    if not (on_this_computer and local_store.has_zip()):
        raise DataError("Upload hackertube-data.zip first.")
    return saved_dataset(local_store.zip_mtime())


@st.cache_data(show_spinner=False, max_entries=1)
def sample_dataset():
    # A small slice of HackerTube's public data that ships with the app (ODC-By 1.0).
    return load_export(demo.sample_zip())


def has_own_zip() -> bool:
    return upload is not None or (on_this_computer and local_store.has_zip())



showing_demo = bool(st.session_state.get("demo")) and "stats" in st.session_state
on_home_now = "stats" not in st.session_state or bool(st.session_state.get("home"))

# Header. The logo, the NerdLore title and the Home button all open the start page.
# The demo button sits next to Home: "Try the demo" on result pages, a bright "DEMO MODE · Exit" while in the demo.
logo, title, demo_col, home_col, _ = st.columns([0.6, 6.2, 2.1, 1.3, 1.5], vertical_alignment="center", gap="small")
if showing_demo:
    demo_col.button("DEMO MODE · Exit", key="demo_exit_top", icon=":material/science:", on_click=go_home,
                    width="stretch", help="You're looking at made-up view counts. Click to leave the demo.")
elif not on_home_now and demo_col.button("Try the demo", key="demo_top", icon=":material/science:", width="stretch",
                                         help="See every page with made-up view counts. Your real results stay saved."):
    try_demo = True
logo.button("💎", key="home_logo", on_click=go_home, help="Home")
with title:
    st.button("NerdLore", key="home_title", type="tertiary", on_click=go_home, help="Home")
    st.html('<div class="htg-sub">Hacker News’ best video picks, ranked by trust, not views.'
            + ('<span class="htg-demo-pill"><i></i>DEMO · MADE-UP VIEWS</span>' if showing_demo else '')
            + '</div>')
home_col.button("Home", key="home_top", icon=":material/home:", on_click=go_home, width="stretch")
if showing_demo and not st.session_state.get("home"):  # stays in the corner while you scroll
    st.html('<div class="htg-demo-float"><i></i>DEMO · the view counts are made up</div>')

if run:
    try:
        with st.spinner("Loading HackerTube data…"):
            ds = load_dataset()
        selected = analysis.filter_videos(ds.videos, types, min_recs, hide_news)
        if selected.empty:
            st.warning("No videos match those filters. Try fewer recommenders or more video types.")
            st.stop()
        bar = st.progress(0.0, text=f"Fetching YouTube view counts for {len(selected):,} videos…")
        stats = fetch_views(selected["vid"], api_key,
                            on_progress=lambda done, total: bar.progress(done / total, text=f"Fetched {done:,} of {total:,}"))
        bar.empty()
        fetched = datetime.now(timezone.utc)
        filters = (tuple(types), min_recs, hide_news)
        st.session_state.update(ds=ds, stats=stats, filters=filters, fetched_at=shown_time(fetched), demo=False,
                                home=False)
        st.session_state.pop("dupes", None)
        st.session_state.pop("views_expire", None)
        if on_this_computer:
            local_store.save_views(stats, filters, fetched)
            st.session_state["views_expire"] = (fetched + local_store.MAX_VIEWS_AGE).strftime("%d %b %Y")
    except (DataError, YouTubeError) as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:  # network trouble while downloading HackerTube data, etc.
        st.error(f"Something went wrong: {type(exc).__name__}. Try again.")
        st.stop()

has_results = "stats" in st.session_state
on_home = not has_results or bool(st.session_state.get("home"))
if on_home:
    in_demo = has_results and bool(st.session_state.get("demo"))
    if not has_results:
        note, button = st.columns([5, 2], vertical_alignment="center")
        note.html('<div class="htg-rule"><b>No YouTube API key yet?</b> Try the demo: every page, with made-up '
                  'view counts, using a small built-in sample of HackerTube\'s data. No setup, nothing saved.</div>')
    elif in_demo:
        note, back = st.columns([5, 2], vertical_alignment="center")
        note.html('<div class="htg-rule"><b>You\'re on the home page.</b> The demo is still open, with its '
                  'made-up view counts.</div>')
        back.button("Back to the demo", type="primary", width="stretch", icon=":material/arrow_forward:",
                    on_click=leave_home, key="back_results")
    else:
        note, button, back = st.columns([4, 2, 2], vertical_alignment="center")
        note.html('<div class="htg-rule"><b>You\'re on the home page.</b> Your results are still here. Or try the '
                  'demo to see every page with made-up view counts (your real ones stay saved).</div>')
        back.button("Back to your results", width="stretch", icon=":material/arrow_forward:",
                    on_click=leave_home, key="back_results")
    if not in_demo and button.button("Try the demo", type="primary", width="stretch", icon=":material/science:",
                                     key="demo_main"):
        try_demo = True
if try_demo:
    ds = load_dataset() if has_own_zip() else sample_dataset()
    selected = analysis.filter_videos(ds.videos, types, min_recs, hide_news)
    if selected.empty:
        st.warning("No videos match those filters. Try fewer recommenders or more video types.")
        st.stop()
    # Made-up numbers stay in memory only: never saved, so real saved views are untouched.
    st.session_state.update(ds=ds, stats=demo.fake_stats(selected), filters=(tuple(types), min_recs, hide_news),
                            demo=True, demo_source="your zip" if has_own_zip() else "the built-in sample",
                            home=False)
    for k in ("fetched_at", "views_expire", "dupes"):
        st.session_state.pop(k, None)
    st.rerun()

if on_home:
    hero = (Path(__file__).parent / "nerdlore" / "hero.html").read_text(encoding="utf-8")
    # A new visit number makes the page reload, so each Home click replays its animation.
    components.html(hero.replace("<body>", f'<body data-visit="{st.session_state.get("home_visit", 0)}">', 1),
                    height=900)
    footer()
    st.stop()

DEMO = bool(st.session_state.get("demo"))
VIEWS = "made-up views" if DEMO else "YouTube views"  # how every view count is labelled
VIEWS_COL = VIEWS[0].upper() + VIEWS[1:]


def page(html: str, height: int) -> None:
    """Show an interactive page; in demo mode it says "made-up views" instead of "YouTube views"."""
    components.html(demo.relabel(html) if DEMO else html, height=height)

ds = st.session_state["ds"]
f_types, f_min, f_news = st.session_state["filters"]
df = analysis.attach_views(analysis.filter_videos(ds.videos, f_types, f_min, f_news), st.session_state["stats"])
kept = (f"  \nKept on this computer until {st.session_state['views_expire']}, then deleted. "
        f"**Run analysis** refreshes them." if st.session_state.get("views_expire") else "")
if DEMO:
    status_slot.caption(":material/science: **Demo mode:** made-up view counts, kept in memory only. Paste your "
                        "key and press **Run analysis** for real ones.")
    st.html('<div class="htg-rule" style="border-left-color:#ff7a3d;background:rgba(255,122,61,.10)">'
            '<b>Demo mode.</b> The view counts and upload dates on every page are <b>made up</b>, not from YouTube, '
            f'and the videos come from {st.session_state.get("demo_source", "the built-in sample")}. '
            'Paste your own YouTube API key and press <b>Run analysis</b> to see the real numbers.</div>')
else:
    status_slot.caption(f":material/schedule: **YouTube views fetched** {st.session_state['fetched_at']}, shown exactly "
                        f"as YouTube reports them.{kept}")

# Streamlit opens on the first tab.
pairs_tab, zones_tab, channels_tab, years_tab, jokes_tab, gems_tab, about_tab = st.tabs(
    ["Same praise, different reach", "Popular vs remembered", "Trusted channels", "Picks by year",
     "HN's inside jokes", "Hidden gems", "About"])

link = st.column_config.LinkColumn
num = st.column_config.NumberColumn


def plain(text: str) -> str:  # keep titles from being read as Markdown links or LaTeX
    return text.replace("[", r"\[").replace("]", r"\]").replace("$", r"\$")


def video_cards(rows: pd.DataFrame, per_row: int = 3) -> None:
    """Thumbnail cards, like hackertube.run. Thumbnails load straight from YouTube's image server."""
    for start in range(0, len(rows), per_row):
        for col, r in zip(st.columns(per_row), rows.iloc[start:start + per_row].itertuples()):
            with col.container(border=True):
                st.image(f"https://i.ytimg.com/vi/{r.vid}/mqdefault.jpg", width="stretch")
                st.markdown(f"**[{plain(r.title)}]({r.url})**")
                st.caption(f"{plain(r.channel)} · {r.content_type}  \n"
                           f"**{r.recommenders}** HN recommenders · **{r.views:,}** {VIEWS}")

with gems_tab:
    section("Loved by Hacker News · barely watched", "Hidden gems",
            "Videos that people on HN keep recommending but few have watched. Set what counts as a gem, "
            "then choose how to rank them.")
    rec_col, view_col, rank_col, save_col = st.columns([3, 3, 3, 2], vertical_alignment="bottom")
    top_recs = int(df["recommenders"].max())
    gem_recs = rec_col.select_slider("At least this many HN recommenders",
                                     list(range(f_min, max(top_recs, f_min + 1) + 1)), value=f_min)
    gem_views = view_col.select_slider(f"Fewer than this many {VIEWS}",
                                       [10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
                                       value=100_000, format_func=lambda v: f"{v:,}")
    # No `required=True`: Streamlit 1.50 doesn't have it. If someone clicks the chosen option off, use the default.
    rank_by = rank_col.segmented_control("Rank by", list(analysis.GEM_RANKINGS), default="recs",
                                         format_func=lambda k: analysis.GEM_RANKINGS[k].replace("YouTube views", VIEWS)
                                         ) or "recs"
    matches = analysis.hidden_gems(df, gem_recs, gem_views, rank_by, limit=None)
    gems = matches.head(48)
    save_col.download_button("Download list",
                             matches[["hn_rank", "title", "channel", "recommenders", "url"]].to_csv(index=False),
                             file_name="nerdlore.csv", mime="text/csv", icon=":material/download:",
                             width="stretch", help="HackerTube data and YouTube links only; no view counts")
    kinds = " or ".join(f_types)
    ranked = ("the <b>most HN recommenders</b> (ties: fewer views)" if rank_by == "recs"
              else f"the <b>fewest {VIEWS}</b> (ties: more HN recommenders)")
    shown = f"; showing the first {len(gems)}" if len(matches) > len(gems) else ""
    qualify = "video qualifies" if len(matches) == 1 else "videos qualify"
    st.html(f'<div class="htg-rule"><b>How the ranking works:</b> a gem is any {kinds} video with at least '
            f'<b>{gem_recs}</b> HN recommenders and fewer than <b>{gem_views:,}</b> {VIEWS}. '
            f'<b>#1</b> is the gem with {ranked}. <b>{len(matches):,}</b> {qualify}{shown}.</div>')
    if gems.empty:
        st.info(f"No videos match. Allow more {VIEWS} or fewer HN recommenders.")
    else:
        page(charts.gems_html(gems, analysis.hn_links(ds.mentions, list(gems["vid"])),
                                         top_recs, int(df["views"].max()), rank_by),
                        height=440 + -(-len(gems) // 4) * 300)
    with st.expander("As a table"):
        st.dataframe(
            gems[["hn_rank", "title", "channel", "recommenders", "views", "url"]],
            hide_index=True, width="stretch",
            column_config={"hn_rank": num("HackerTube rank", help=f"Out of {len(ds.videos):,}, by HackerTube's score"),
                           "recommenders": num("HN recommenders", help="HackerTube data, not YouTube"),
                           "views": num(VIEWS_COL, format="%d", help="Made up for the demo" if DEMO else "From YouTube"),
                           "url": link("Watch", display_text="YouTube ↗")})

    with st.expander("Check for other uploads of the top gems (uses more quota)"):
        st.write("A talk can look unwatched because a different upload has the views. "
                 "This searches YouTube for each title. It costs about 100 quota units per talk "
                 "(your free daily quota is 10,000).")
        if DEMO:
            st.caption("This searches YouTube with your own API key, so it isn't part of the demo.")
        n_check = st.number_input("Talks to check", 1, 20, 5, disabled=DEMO)
        if st.button("Search for other uploads", disabled=DEMO):
            try:
                with st.spinner("Searching YouTube…"):
                    st.session_state["dupes"] = {
                        row.vid: search_other_uploads(f"{row.title} {row.channel}", api_key)
                        for row in gems.head(int(n_check)).itertuples()}
            except YouTubeError as exc:
                st.error(str(exc))
        for row in gems.itertuples():
            found = st.session_state.get("dupes", {}).get(row.vid)
            if found is None:
                continue
            others = [d for d in found if d["vid"] != row.vid]
            st.markdown(f"**{row.title}** ({row.views:,} views)")
            if others:
                st.dataframe(pd.DataFrame(others)[["title", "channel", "views"]], hide_index=True,
                             width="stretch", column_config={"views": num(VIEWS_COL, format="%d")})
            else:
                st.caption("No other uploads found in the top results.")

with pairs_tab:
    section("Same HN love · different audiences", "Same praise, different reach",
            "Two videos recommended by exactly the same number of people on HN: the one most people watched, "
            "and the one almost nobody did. Click a row in the chart, use ◀ ▶, or let it play.")
    pairs = analysis.pairs(df, f_min)
    if pairs.empty:
        st.info("Not enough videos for pairs. Lower the minimum recommenders.")
    else:
        page(charts.pairs_html(pairs), height=640 + len(pairs) * 26)
        with st.expander("As a table"):
            st.dataframe(pairs[[c for c in pairs.columns if not c.endswith(("_vid", "_why", "_type", "_published"))]],
                         hide_index=True, width="stretch", column_config={
                "recommenders": num("HN recommenders"),
                "most_viewed_title": "Most viewed", "most_viewed_channel": "Channel",
                "most_viewed_views": num(VIEWS_COL, format="%d"),
                "most_viewed_url": link("", display_text="↗"),
                "least_viewed_title": "Least viewed", "least_viewed_channel": "Channel ",
                "least_viewed_views": num(VIEWS_COL + " ", format="%d"),
                "least_viewed_url": link(" ", display_text="↗")})

with zones_tab:
    section("Remembered vs watched", "Popular vs remembered",
            "Two questions about every video: <b>do engineers on Hacker News keep recommending it?</b> and "
            "<b>have lots of people watched it?</b> The answers put it in one of four zones. "
            "You decide what counts as &ldquo;many&rdquo;.")
    left, right = st.columns(2)
    rec_options = list(range(int(df["recommenders"].min()), int(df["recommenders"].max()) + 1))
    many_recs = left.select_slider("Many HN recommenders means at least", rec_options,
                                   value=min(max(10, rec_options[0]), rec_options[-1]))
    many_views = right.select_slider(f"Lots of {VIEWS} means at least",
                                     [10_000, 50_000, 100_000, 500_000, 1_000_000, 10_000_000], value=100_000,
                                     format_func=lambda v: f"{v:,}")
    zones = analysis.zone_of(df, many_recs, many_views)
    featured = {z: list(analysis.videos_in_zone(df, zones, z)["vid"].head(4)) for z in analysis.ZONES}
    page(charts.zone_map_html(df, zones, many_recs, many_views, featured), height=580)
    st.caption("Each dot is one video, spread a little up and down so dots don't hide each other. The thumbnails "
               "are each zone's top videos, tied to their dots. Hover for details, click to watch. Move a slider "
               "and the map shows which videos change zone.")

    zone = st.segmented_control("Show me the videos in", analysis.ZONES, default="Hidden gems")
    if zone:
        in_zone = analysis.videos_in_zone(df, zones, zone)
        if in_zone.empty:
            st.info("No videos in this zone with these settings. Try moving the sliders.")
        else:
            st.caption(f"{len(in_zone):,} videos. Showing the first {min(len(in_zone), 12)}.")
            video_cards(in_zone.head(12))
            if len(in_zone) > 12:
                with st.expander(f"All {len(in_zone):,} videos in {zone}"):
                    st.dataframe(in_zone[["title", "channel", "recommenders", "views", "url"]], hide_index=True,
                                 width="stretch",
                                 column_config={"recommenders": num("HN recommenders"),
                                                "views": num(VIEWS_COL, format="%d"),
                                                "url": link("Watch", display_text="YouTube ↗")})

with channels_tab:
    section("HackerTube data only", "Channels Hacker News trusts most",
            "Channels with 10 or more videos, ranked by their average HackerTube score. "
            "Pick a channel to see its best videos.")
    channels = analysis.trusted_channels(ds.videos)
    page(charts.channels_html(channels, analysis.channel_top_videos(ds.videos, list(channels["channel"]))),
                    height=760)
    with st.expander("As a table"):
        st.dataframe(
            channels[["channel", "videos", "avg_hn_score", "channel_url", "best_url", "best_title"]],
            hide_index=True, width="stretch",
            column_config={"channel": "Channel", "videos": num("Videos", help="Videos from this channel in HackerTube"),
                           "avg_hn_score": num("Avg HackerTube score"),
                           "channel_url": link("YouTube", display_text="Find ↗",
                                               help="The data has channel names only, so this searches YouTube"),
                           "best_url": link("Top video", display_text="Watch ↗"),
                           "best_title": "Its top video on HackerTube"})

with years_tab:
    section("Year by year", "HN's picks from any year",
            f"A time machine for your {' and '.join(f_types)} videos: click or drag along the timeline, use ◀ ▶, "
            "or press play. Switch between the year a video was uploaded and the year HN first found it.")
    if df["uploaded_year"].isna().all():
        st.info("No upload dates yet, so only “First recommended on HN” works. Press **Run analysis** to fetch them.")
    page(charts.years_html(df, " / ".join(f_types)), height=900)

with jokes_tab:
    section("Punchlines, not recommendations", "HN's inside jokes",
            "Some videos on Hacker News aren't recommendations but running gags: when a thread hits a familiar topic, "
            "someone posts the same old clip. Pick a clip to see the joke, when it gets posted, and real threads. "
            "HackerTube data only; an LLM labelled each comment, so expect some mistakes.")
    jokes = analysis.hn_inside_jokes(ds.mentions, ds.videos)
    if jokes.empty:
        st.info("This export has no mentions.jsonl, so joke labels aren't available.")
    else:
        page(charts.jokes_html(
            jokes, {v: analysis.joke_years(ds.mentions, v) for v in jokes["vid"]},
            {v: analysis.joke_threads(ds.mentions, v, limit=6) for v in jokes["vid"]}), height=900)

with about_tab:
    section("About", "How NerdLore works")
    st.markdown(
        f"- **Hacker News side:** the [HackerTube]({HACKERTUBE}) export lists every YouTube video HN commenters "
        f"recommended, with how many different people recommended it, plus labels written by an LLM.\n"
        f"- **YouTube side:** with your own API key, the app asks YouTube for each video's view count and upload "
        f"date, and shows them exactly as YouTube returns them. It never computes averages or scores from them.\n"
        f"- **Together:** the tabs put the two side by side, so you can find talks engineers swear by that few "
        f"people have watched.\n"
        f"- **Your data:** your key and the view counts stay on your own computer; view counts are deleted "
        f"after 30 days.")
    if st.button("Read the full privacy notice", icon=":material/shield:", key="privacy_about"):
        privacy_dialog()

footer(DEMO)
