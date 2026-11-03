# Contributing to NerdLore

Thanks for helping. Bug reports, ideas and pull requests are all welcome.

## Set up

```bash
git clone https://github.com/saeedkhattak/nerdlore.git
cd nerdlore
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt pytest
pytest
streamlit run app.py
```

The tests use small made-up data and a fake YouTube API, so they need no key and no
internet. To try the app itself you need your own key and the HackerTube zip: see the
[README](README.md#-before-you-start).

## Ground rules

These keep NerdLore within YouTube's API policies and HackerTube's data licence. Pull requests
that break them can't be merged.

1. **Show YouTube numbers exactly as YouTube returns them.** Sorting and filtering by view
   counts is fine. Calculating anything from them (averages, totals, ratios, scores, "views
   per recommender") is not.
2. **Keep YouTube data for at most 30 days**, and only on the user's own computer
   (`nerdlore/local_store.py` handles this).
3. **Never put view counts in downloads or exports.** HackerTube data and YouTube links are
   fine.
4. **Label where each number comes from:** HackerTube or YouTube.
5. **Never log the API key** or put it in an error message or web address. There's a test for
   this; keep it passing.
6. **Credit HackerTube** (ODC-By 1.0) wherever its data appears.
7. **Never commit data or keys:** no zips, `.jsonl` files, view counts or API keys. The
   `.gitignore` blocks the usual ones.

## Code style

- The interactive pages in `nerdlore/*.html` are plain HTML, CSS and canvas with no
  libraries. `charts.py` puts each page's data into its `__DATA__` placeholder.
- Keep pages readable in both light and dark themes, and respect `prefers-reduced-motion`.
- Add or update a test in `tests/` for any change to `analysis.py`, `charts.py`, `data.py`,
  `youtube.py` or `local_store.py`.

## Pull requests

- Keep each pull request to one change, and say what it does and why.
- Run `pytest` before you push. GitHub Actions runs it on Python 3.10 and 3.13.
- For visual changes, add a screenshot.

## Reporting a bug

[Open an issue](https://github.com/saeedkhattak/nerdlore/issues) with what you did, what you
expected, the message you saw, and your Python and Streamlit versions (`python --version`,
`streamlit version`). **Never include your API key.**
