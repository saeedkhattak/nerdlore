### Privacy notice

**NerdLore uses YouTube API Services.** By using it you agree to the
[YouTube Terms of Service](https://www.youtube.com/t/terms). Google's handling of data is
covered by the [Google Privacy Policy](https://policies.google.com/privacy).

**What this app accesses**

- **Your YouTube API key.** You type it in. It is sent only to Google's YouTube Data API
  over HTTPS, and never logged or put in a web address. It stays in memory for your session
  unless you press **Save key**; see below.
- **Public YouTube data:** view counts and upload dates for the videos you analyse (and, only if you ask,
  titles and view counts of other uploads of the same talks). No personal data, no
  account sign-in, no watch history. Video thumbnails load straight from YouTube's image
  server, as they would on any page that shows YouTube videos.
- **HackerTube's public data export,** which you upload.

**What it stores**

On your own computer only, in the `.nerdlore` folder in your home folder:

- your API key, **only if you press Save key**. **Forget key** deletes it.
- a copy of the last HackerTube zip you uploaded (public data), so you don't have to
  upload it again.
- the YouTube view counts and upload dates from your last run, so a refresh doesn't lose
  them. They are deleted automatically after 30 days, as YouTube's API policies require,
  or straight away when you press **Forget YouTube data**. **Run analysis** replaces them
  with fresh ones.

Nothing is saved when the app is opened from any address other than `localhost`. The app
adds no tracking or analytics (Streamlit's own usage statistics are switched off in
`.streamlit/config.toml`).

**Where it runs**

On your own computer, when you start it with `streamlit run app.py`. If someone hosts
it on a server, your key passes through that server: only use hosted copies you trust.

**Questions** about this notice: open an issue on the project's GitHub page.
