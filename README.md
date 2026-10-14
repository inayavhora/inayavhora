# AI News Wire

A self-updating archive of AI headlines from international newsrooms, for the Speculation section of Inaya Vhora's website.

## What's in here

| File | What it does |
|---|---|
| `fetch_news.py` | The research robot. Reads 12 news feeds (UK, US, Germany, Qatar, Australia, Hong Kong, plus Google News worldwide), keeps the AI stories, and adds them to `news.json`. |
| `.github/workflows/update-news.yml` | Runs the robot every hour on GitHub's servers, for free. |
| `news.json` | The archive. Starts empty and fills on the first run. Keeps the latest 400 headlines. |
| `index.html` | The page visitors see. It reads `news.json` and checks for new headlines every 5 minutes. |

## Setup (about 10 minutes, no coding)

1. Create a free account at github.com, then click **New repository**. Name it something like `inayavhora-site` and make it **Public**.
2. Click **uploading an existing file** and drag in everything from this folder, including the `.github` folder. (If your computer hides it, upload `update-news.yml` and then move it into `.github/workflows/` using GitHub's "Add file → Create new file" and typing that path.)
3. Go to **Settings → Pages**, set Source to **Deploy from a branch**, branch **main**, folder **/ (root)**. Your page will be live at `https://<username>.github.io/<repo>/` within a minute or two.
4. Go to the **Actions** tab, choose **Update AI news wire**, and click **Run workflow** to fill the wire straight away. After that it runs by itself every hour.

GitHub Pages can also serve the rest of your site, and you can point a custom domain at it later (Settings → Pages → Custom domain).

## Adjusting it

- **Sources**: edit the `FEEDS` list in `fetch_news.py`. Each line is a name, a region, a feed URL, and whether the feed is AI-only.
- **What counts as AI**: the keyword lists `AI_ACRONYMS` and `AI_WORDS` in the same file.
- **Archive size**: `MAX_ITEMS` in the script; how many show on the page: `SHOW` in `index.html`.
- **Nav links**: the `About` and `Speculation` links at the top of `index.html` point to `about.html` and `speculation.html`; change them to match your pages.

## Notes

- If a news outlet changes or removes its feed, that one is skipped and the rest keep working. The Actions log shows which sources were reached on each run.
- GitHub pauses scheduled jobs on repositories with no activity for 60 days. The hourly commits count as activity, so this normally isn't an issue.
- Opening `index.html` by double-clicking it won't load the headlines (browsers block that). View it through the GitHub Pages link instead.
