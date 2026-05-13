# Deploy guide — Streamlit Cloud

Free public hosting for the Equity Valuation web app on [streamlit.io/cloud](https://streamlit.io/cloud).

## Prerequisites

1. GitHub account (free)
2. Push this repo to GitHub public (see "Step 1" below)
3. Streamlit Cloud account (free, signs in with GitHub)

## Step 1. Push repo to GitHub

```powershell
# From this folder (dcf-inditex-fsi)
gh auth status                              # verify gh is authenticated
gh repo create dcf-equity-valuation --public --source=. --remote=origin --description "Equity Valuation Toolkit: DCF + Comps web app powered by Anthropic financial-services agents" --push
```

If `gh` not installed:
```powershell
winget install --id GitHub.cli
gh auth login
```

After push, note the repo URL: `https://github.com/<your-username>/dcf-equity-valuation`.

## Step 2. Connect Streamlit Cloud

1. Visit https://share.streamlit.io
2. Sign in with GitHub (authorize Streamlit to access your repos)
3. Click **New app**
4. Fill the form:
   - Repository: `<your-username>/dcf-equity-valuation`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: customize, e.g. `equity-valuation` → `equity-valuation.streamlit.app`
5. Click **Deploy**

Streamlit Cloud will:
1. Clone the repo
2. Install Python 3.11 + dependencies from `requirements.txt`
3. Run `streamlit run streamlit_app.py`
4. Expose public URL

First deploy takes 2-5 minutes. Subsequent pushes auto-redeploy in ~1 minute.

## Step 3. Test deployed app

Visit `https://equity-valuation.streamlit.app` (or whatever URL you chose).

Test cases:
1. Default `AAPL` + peers `MSFT,GOOG,META,AMZN,NFLX` → click **Fetch data**
2. Wait ~30 seconds for yfinance to return data
3. Adjust WACC sliders, scenario assumptions
4. Verify charts render
5. Download xlsx + memo

## Step 4. Share

URL format: `https://<your-app-name>.streamlit.app`

Add to:
- LinkedIn profile featured section
- CV "Selected Projects"
- Cover letters for Tier B AI / finance roles

## Free tier limits (Streamlit Cloud)

- Public apps: unlimited
- Private apps: 1 free (paid plans for more)
- Resources: 1 GB RAM, 1 CPU per app
- Bandwidth: unmetered for personal use
- Sleeps after 7 days no traffic (auto-wakes on visit)

## Troubleshooting

### "ModuleNotFoundError: No module named X"

Add to `requirements.txt` and push. Cloud auto-redeploys.

### "yfinance returns empty data"

Yahoo Finance throttles or blocks IPs occasionally. Streamlit Cloud uses shared IPs so this is rare. If persistent:
- Try alternative ticker format (e.g. `AAPL` vs `AAPL.US`)
- Add retry logic in `data_fetcher.py`

### App crashes silently

Check logs in Streamlit Cloud dashboard. Most common: missing dep or pyarrow installation failure (should work on Linux).

### Local dev fails (Windows ARM64)

pyarrow has no Windows ARM64 wheels. For local development:
- Use Linux/macOS or x86_64 Windows
- Or skip local testing and rely on Streamlit Cloud (preview deploys before share)

## Cost

Total: **EUR 0 / USD 0**. Free tier covers all use cases for this app indefinitely.

## Alternative free hosts

If Streamlit Cloud sleeping is annoying:

| Provider | Free tier | Streamlit support |
|---|---|---|
| Streamlit Cloud | Best | Native |
| Render | 750h/mo | Manual Procfile |
| Railway | $5 credit/mo | Manual Dockerfile |
| Hugging Face Spaces | Free CPU | Native Streamlit |
| Fly.io | Free 3 small VMs | Manual Dockerfile |

For this case study: Streamlit Cloud is the simplest and most aligned with the tool.

## Updating the app

Push to GitHub main branch:

```powershell
git add .
git commit -m "Update: <what changed>"
git push
```

Streamlit Cloud detects the push and redeploys automatically in ~1 minute.

## Next steps post-deploy

1. Tweet / LinkedIn post with URL (drafts in `LINKEDIN-POST.md`)
2. Add custom domain (Streamlit Cloud supports CNAME)
3. Add Google Analytics (paste tracking snippet in `streamlit_app.py`)
4. Add password protection (Streamlit secrets + simple auth)
5. Add more cases via the toolkit (cases/<company>/)
