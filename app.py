"""NerdLore: Streamlit app. Run with:  streamlit run app.py"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from nerdlore import analysis, charts, local_store
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


def footer() -> None:
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
        f'dates come from the YouTube Data API, shown exactly as YouTube returns them.</div>')
    if button.button("Privacy notice", type="tertiary", icon=":material/shield:", key="privacy_footer"):
        privacy_dialog()


# ---------- sidebar: inputs ----------
st.sidebar.title("💎 NerdLore")
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
if st.sidebar.button("Forget YouTube data", width="stretch"):
    for k in ("stats", "fetched_at", "views_expire", "dupes"):
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


st.html('<div class="htg-head"><div class="htg-logo">💎</div><div><div class="htg-title">NerdLore</div>'
        '<div class="htg-sub">Hacker News’ best video picks, ranked by trust, not views.'
        '</div></div></div>')

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
        st.session_state.update(ds=ds, stats=stats, filters=filters, fetched_at=shown_time(fetched))
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

if "stats" not in st.session_state:
    components.html((Path(__file__).parent / "nerdlore" / "hero.html").read_text(encoding="utf-8"),
                    height=900)
    footer()
    st.stop()

ds = st.session_state["ds"]
f_types, f_min, f_news = st.session_state["filters"]
df = analysis.attach_views(analysis.filter_videos(ds.videos, f_types, f_min, f_news), st.session_state["stats"])
kept = (f"  \nKept on this computer until {st.session_state['views_expire']}, then deleted. "
        f"**Run analysis** refreshes them." if st.session_state.get("views_expire") else "")
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
                           f"**{r.recommenders}** HN recommenders · **{r.views:,}** YouTube views")

with gems_tab:
    section("Loved by Hacker News · barely watched", "Hidden gems",
            "Videos that people on HN keep recommending but few have watched. Set what counts as a gem, "
            "then choose how to rank them.")
    rec_col, view_col, rank_col, save_col = st.columns([3, 3, 3, 2], vertical_alignment="bottom")
    top_recs = int(df["recommenders"].max())
    gem_recs = rec_col.select_slider("At least this many HN recommenders",
                                     list(range(f_min, max(top_recs, f_min + 1) + 1)), value=f_min)
    gem_views = view_col.select_slider("Fewer than this many YouTube views",
                                       [10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
                                       value=100_000, format_func=lambda v: f"{v:,}")
    rank_by = rank_col.segmented_control("Rank by", list(analysis.GEM_RANKINGS), default="recs", required=True,
                                         format_func=analysis.GEM_RANKINGS.get)
    matches = analysis.hidden_gems(df, gem_recs, gem_views, rank_by, limit=None)
    gems = matches.head(48)
    save_col.download_button("Download list",
                             matches[["hn_rank", "title", "channel", "recommenders", "url"]].to_csv(index=False),
                             file_name="nerdlore.csv", mime="text/csv", icon=":material/download:",
                             width="stretch", help="HackerTube data and YouTube links only; no view counts")
    kinds = " or ".join(f_types)
    ranked = ("the <b>most HN recommenders</b> (ties: fewer views)" if rank_by == "recs"
              else "the <b>fewest YouTube views</b> (ties: more HN recommenders)")
    shown = f"; showing the first {len(gems)}" if len(matches) > len(gems) else ""
    qualify = "video qualifies" if len(matches) == 1 else "videos qualify"
    st.html(f'<div class="htg-rule"><b>How the ranking works:</b> a gem is any {kinds} video with at least '
            f'<b>{gem_recs}</b> HN recommenders and fewer than <b>{gem_views:,}</b> YouTube views. '
            f'<b>#1</b> is the gem with {ranked}. <b>{len(matches):,}</b> {qualify}{shown}.</div>')
    if gems.empty:
        st.info("No videos match. Allow more YouTube views or fewer HN recommenders.")
    else:
        components.html(charts.gems_html(gems, analysis.hn_links(ds.mentions, list(gems["vid"])),
                                         top_recs, int(df["views"].max()), rank_by),
                        height=440 + -(-len(gems) // 4) * 300)
    with st.expander("As a table"):
        st.dataframe(
            gems[["hn_rank", "title", "channel", "recommenders", "views", "url"]],
            hide_index=True, width="stretch",
            column_config={"hn_rank": num("HackerTube rank", help=f"Out of {len(ds.videos):,}, by HackerTube's score"),
                           "recommenders": num("HN recommenders", help="HackerTube data, not YouTube"),
                           "views": num("YouTube views", format="%d", help="From YouTube"),
                           "url": link("Watch", display_text="YouTube ↗")})

    with st.expander("Check for other uploads of the top gems (uses more quota)"):
        st.write("A talk can look unwatched because a different upload has the views. "
                 "This searches YouTube for each title. It costs about 100 quota units per talk "
                 "(your free daily quota is 10,000).")
        n_check = st.number_input("Talks to check", 1, 20, 5)
        if st.button("Search for other uploads"):
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
                             width="stretch", column_config={"views": num("YouTube views", format="%d")})
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
        components.html(charts.pairs_html(pairs), height=640 + len(pairs) * 26)
        with st.expander("As a table"):
            st.dataframe(pairs[[c for c in pairs.columns if not c.endswith(("_vid", "_why", "_type", "_published"))]],
                         hide_index=True, width="stretch", column_config={
                "recommenders": num("HN recommenders"),
                "most_viewed_title": "Most viewed", "most_viewed_channel": "Channel",
                "most_viewed_views": num("YouTube views", format="%d"),
                "most_viewed_url": link("", display_text="↗"),
                "least_viewed_title": "Least viewed", "least_viewed_channel": "Channel ",
                "least_viewed_views": num("YouTube views ", format="%d"),
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
    many_views = right.select_slider("Lots of YouTube views means at least",
                                     [10_000, 50_000, 100_000, 500_000, 1_000_000, 10_000_000], value=100_000,
                                     format_func=lambda v: f"{v:,}")
    zones = analysis.zone_of(df, many_recs, many_views)
    featured = {z: list(analysis.videos_in_zone(df, zones, z)["vid"].head(4)) for z in analysis.ZONES}
    components.html(charts.zone_map_html(df, zones, many_recs, many_views, featured), height=580)
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
                                                "views": num("YouTube views", format="%d"),
                                                "url": link("Watch", display_text="YouTube ↗")})

with channels_tab:
    section("HackerTube data only", "Channels Hacker News trusts most",
            "Channels with 10 or more videos, ranked by their average HackerTube score. "
            "Pick a channel to see its best videos.")
    channels = analysis.trusted_channels(ds.videos)
    components.html(charts.channels_html(channels, analysis.channel_top_videos(ds.videos, list(channels["channel"]))),
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
    components.html(charts.years_html(df, " / ".join(f_types)), height=900)

with jokes_tab:
    section("Punchlines, not recommendations", "HN's inside jokes",
            "Some videos on Hacker News aren't recommendations but running gags: when a thread hits a familiar topic, "
            "someone posts the same old clip. Pick a clip to see the joke, when it gets posted, and real threads. "
            "HackerTube data only; an LLM labelled each comment, so expect some mistakes.")
    jokes = analysis.hn_inside_jokes(ds.mentions, ds.videos)
    if jokes.empty:
        st.info("This export has no mentions.jsonl, so joke labels aren't available.")
    else:
        components.html(charts.jokes_html(
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

footer()
