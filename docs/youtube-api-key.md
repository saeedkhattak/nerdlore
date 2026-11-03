# Get a YouTube API key

NerdLore asks YouTube for view counts and upload dates with **your own** API key. The key is
free, takes about five minutes to make, and works with any Google account. You don't need a
credit card, and you don't need to set up billing.

## 1. Create a Google Cloud project

1. Open the [Google Cloud console](https://console.cloud.google.com/) and sign in.
2. At the top of the page, open the project picker and choose **New project**.
3. Name it something like `nerdlore` and press **Create**. Make sure the new project is
   selected in the picker before you go on.

## 2. Turn on the YouTube Data API

1. Go to **APIs & Services → Library**
   ([direct link](https://console.cloud.google.com/apis/library/youtube.googleapis.com)).
2. Search for **YouTube Data API v3**, open it and press **Enable**.

## 3. Create the key

1. Go to **APIs & Services → Credentials**.
2. Press **Create credentials → API key**. Google shows the new key: a long string that starts
   with `AIza`.
3. Copy it. You can always come back to this page to copy it again.

## 4. Restrict the key (recommended)

A restricted key is useless to anyone else, even if it leaks.

1. On the **Credentials** page, click the key's name.
2. Under **API restrictions**, choose **Restrict key** and tick **YouTube Data API v3**.
3. Press **Save**. It can take a few minutes before the change takes effect.

## 5. Use it in NerdLore

Paste the key into **Your YouTube API key** in the app's sidebar.

- Press **Save key** to keep it on this computer, in `~/.nerdlore` in your home folder (not in
  the project folder). Without it, the key is forgotten when you refresh the page.
- Press **Forget key** to delete the saved copy.

## Keep it private

- Never commit the key to git, paste it into an issue, or share it in a screenshot.
- The repo's `.gitignore` blocks common key files, and NerdLore never writes the key inside the
  project folder.
- If a key leaks, delete it on the **Credentials** page and create a new one.

## How much quota does NerdLore use?

The free quota is **10,000 units per day** per project.

| Action | Cost |
|---|---|
| **Run analysis** | 1 unit per 50 videos |
| Reopening the app or refreshing the page | 0 units |
| **Search for other uploads** (optional, Hidden gems page) | About 100 units per video checked |

Google's own guide: [YouTube Data API: getting started](https://developers.google.com/youtube/v3/getting-started).
