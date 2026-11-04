"""Build the small HackerTube sample that NerdLore's demo mode uses.

    python scripts/make_demo_sample.py path/to/hackertube-data.zip

Writes nerdlore/sample_data/hackertube-sample.zip: the same format as HackerTube's export, but only
the videos the demo needs (every page has something to show) and a few mentions per video.
Video rows are copied unchanged; mention rows keep only the fields the app reads. HackerTube's
data is licensed ODC-By 1.0; the notice inside the zip credits it.
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nerdlore import analysis  # noqa: E402
from nerdlore.data import _find, _read_jsonl, load_export  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "nerdlore" / "sample_data" / "hackertube-sample.zip"
MIN_RECS = 8           # every video at least this well recommended
MENTIONS_PER_VIDEO = 3  # enough for each page's quote and thread links
STANCE_ORDER = {"strong_rec": 0, "rec": 1, "reference": 2, "critical": 3, "joke": 4}
# Only the mention fields NerdLore reads: no usernames and no full comment text.
MENTION_FIELDS = ("vid", "stance", "month", "story_title", "quote", "hn_url", "hn_comment_id")

NOTICE = """# HackerTube sample for NerdLore's demo mode

A small sample of the HackerTube export (https://hackertube.org/data), made on {made} with
scripts/make_demo_sample.py. {videos} of {all_videos} videos and {mentions} of {all_mentions}
mentions. Video rows are copied unchanged. Mention rows keep only the fields NerdLore reads
(video, stance, month, thread title, short quote and link): no usernames or full comments.

HackerTube's data is derived from the open-index/hacker-news dataset
(https://huggingface.co/datasets/open-index/hacker-news, Hacker News data by Y Combinator) and
licensed under the Open Data Commons Attribution License (ODC-By 1.0):
https://opendatacommons.org/licenses/by/1-0/

Hacker News comments quoted here remain the work of their authors. HackerTube's labels were
written by an LLM. NerdLore is not affiliated with HackerTube, Hacker News or Y Combinator.

This sample contains no YouTube data. The view counts NerdLore shows in demo mode are made
up on your computer when you press "Try the demo".
"""


def main(src: Path) -> None:
    raw = src.read_bytes()
    ds = load_export(raw)
    videos, mentions = ds.videos, ds.mentions

    keep = set(videos.loc[videos["recommenders"] >= MIN_RECS, "vid"])
    channels = analysis.trusted_channels(videos)["channel"]
    keep |= set(videos.loc[videos["channel"].isin(channels), "vid"])
    jokes = set(analysis.hn_inside_jokes(mentions, videos)["vid"])
    keep |= jokes

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        video_rows = [r for r in _read_jsonl(zf, _find(names, "videos.jsonl")) if r["vid"] in keep]
        mention_rows = [{k: r[k] for k in MENTION_FIELDS if k in r}
                        for r in _read_jsonl(zf, _find(names, "mentions.jsonl")) if r.get("vid") in keep]

    picked, per_video = [], {}
    rank = lambda r: (STANCE_ORDER.get(r.get("stance"), 9), not (r.get("quote") or "").strip(), r.get("month", ""))
    for r in sorted(mention_rows, key=rank):
        if r["vid"] in jokes and r.get("stance") == "joke":
            picked.append(r)  # joke counts and the per-year chart need every joke mention
        elif per_video.get(r["vid"], 0) < MENTIONS_PER_VIDEO and r.get("stance") != "joke":
            picked.append(r)
            per_video[r["vid"]] = per_video.get(r["vid"], 0) + 1

    def jsonl(rows: list[dict]) -> str:
        return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    notice = NOTICE.format(made=date.today().isoformat(), videos=len(video_rows), all_videos=len(videos),
                           mentions=len(picked), all_mentions=len(mentions))
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        out.writestr("hackertube-sample/NOTICE.md", notice)
        out.writestr("hackertube-sample/videos.jsonl", jsonl(video_rows))
        out.writestr("hackertube-sample/mentions.jsonl", jsonl(picked))
    print(f"{OUT.name}: {len(video_rows)} videos, {len(picked)} mentions, {OUT.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
