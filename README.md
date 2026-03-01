# LinkedIn Weekly Automation System

Automatically generates four LinkedIn post options every Monday and delivers them to matthieu.jammers@gmail.com — ready to copy, choose, and post on Tuesday and Thursday at 11:00 AM Bali time.

---

## HOW IT WORKS

Every **Monday at 00:00 UTC (08:00 AM Bali time)**, GitHub runs the automation automatically:

1. Scrapes Matthieu's LinkedIn profile for voice and recent topics
2. Scrapes industry LinkedIn content for trending Bali/Indonesia real estate topics
3. Generates four post options via Gemini AI — two for Tuesday, two for Thursday
4. Sends one email to matthieu.jammers@gmail.com with all four options formatted and ready to copy
5. Logs the run so themes and pillars rotate correctly next week

Matthieu reads the email on Monday morning, picks one option for Tuesday and one for Thursday, and posts them manually on LinkedIn at 11:00 AM Bali time.

---

## FIRST-TIME SETUP

You need to complete these steps once before the system works. After that, it runs fully automatically every Monday with no action required.

---

### STEP 1 — GET YOUR GEMINI API KEY

This key lets the system use Google's AI to write the posts.

1. Go to **https://aistudio.google.com**
2. Sign in with **hello@scalrize.com** (your Gemini Pro account)
3. Click **"Get API Key"** in the top menu
4. Click **"Create API key"**
5. Copy the key — it looks like: `AIzaSy...`

**Save this. You will add it to GitHub in Step 5 as `GEMINI_API_KEY`.**

---

### STEP 2 — SET UP GMAIL API CREDENTIALS

This allows the system to send emails from matthieu.jammers@gmail.com.

1. Go to **https://console.cloud.google.com**
2. Sign in with **matthieu.jammers@gmail.com**
3. Click the project dropdown at the top → click **"New Project"**
4. Name it: `LinkedIn Automation` → click **"Create"**
5. Make sure the new project is selected in the dropdown
6. In the search bar, search for **"Gmail API"** → click it → click **"Enable"**
7. In the left menu, go to **APIs & Services → Credentials**
8. Click **"+ Create Credentials"** → choose **"OAuth client ID"**
9. If prompted to configure the consent screen first:
   - Click **"Configure Consent Screen"**
   - Choose **"External"** → click **"Create"**
   - Fill in App name: `LinkedIn Automation`, User support email: `matthieu.jammers@gmail.com`
   - Scroll down → click **"Save and Continue"** three times → click **"Back to Dashboard"**
   - Go back to **Credentials → + Create Credentials → OAuth client ID**
10. Application type: **Desktop app**
11. Name: `LinkedIn Automation`
12. Click **"Create"**
13. Click **"Download JSON"** — this downloads a file called `credentials.json`
14. Open the file with any text editor (TextEdit on Mac, Notepad on Windows)
15. Copy the **entire contents** of the file

**Save this. You will add it to GitHub in Step 5 as `GMAIL_CREDENTIALS`.**

---

### STEP 3 — ONE-TIME GMAIL AUTHORIZATION

This step generates an access token so the system can send emails on your behalf. You only do this once.

**Prerequisites:** Python must be installed on your computer.
- Mac: open Terminal, type `python3 --version` to check
- If not installed: download from https://python.org

**Run these commands in your terminal (one at a time):**

```bash
# Navigate to the linkedin-automation folder
cd ~/Desktop/linkedin-automation

# Install required libraries
pip3 install google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Run the authorization script
python3 authorize_gmail.py
```

When you run the script:
1. A browser window opens automatically
2. Sign in with **matthieu.jammers@gmail.com**
3. Click **"Allow"** to grant permission
4. The browser will show a confirmation message
5. Return to your terminal — you will see: `Token saved to token.json`

Now open the `token.json` file that was created in the folder:
- Open it with any text editor
- Copy the **entire contents** of the file

**Save this. You will add it to GitHub in Step 5 as `GMAIL_TOKEN`.**

---

### STEP 4 — GET YOUR FIRECRAWL API KEY

Firecrawl scrapes LinkedIn and news sites to keep posts relevant and timely.

1. Go to **https://firecrawl.dev** and sign in to your existing account
2. Click your profile or go to the **Dashboard**
3. Navigate to **API Keys**
4. Copy your existing API key — it looks like: `fc-...`

If you don't have a Firecrawl account, create a free one at https://firecrawl.dev.

**Save this. You will add it to GitHub in Step 5 as `FIRECRAWL_API_KEY`.**

---

### STEP 5 — ADD ALL SECRETS TO GITHUB

GitHub Secrets store your credentials securely so the automation can use them without ever exposing them in the code.

1. Go to **https://github.com/scalrize/linkedin-automation**
2. Click **"Settings"** (top menu bar of the repository)
3. In the left sidebar, click **"Secrets and variables"** → **"Actions"**
4. Click **"New repository secret"** for each of the four secrets below:

| Secret Name | Value to paste |
|---|---|
| `GEMINI_API_KEY` | The key from Step 1 |
| `GMAIL_CREDENTIALS` | The full contents of credentials.json from Step 2 |
| `GMAIL_TOKEN` | The full contents of token.json from Step 3 |
| `FIRECRAWL_API_KEY` | The key from Step 4 |

For each one: type the exact Secret Name shown above → paste the value → click **"Add secret"**.

---

### STEP 6 — TEST THE SYSTEM

Once all four secrets are added:

1. Go to **https://github.com/scalrize/linkedin-automation**
2. Click the **"Actions"** tab
3. In the left sidebar, click **"LinkedIn Weekly Post Generator"**
4. Click **"Run workflow"** (top right) → click the green **"Run workflow"** button
5. Wait 2–3 minutes for the run to complete
6. Check **matthieu.jammers@gmail.com** for the test email

A green checkmark = everything worked. A red X = check the troubleshooting section below.

---

## WHAT HAPPENS EVERY MONDAY

- You receive one email at 08:00 AM Bali time
- The email contains four posts: two options for Tuesday, two for Thursday
- Each option shows the post text, character count, read time, suggested visual, and why it was chosen
- A recommendation tells you which option is stronger that week
- Posts rotate through four themes and four content pillars automatically — no repeats

---

## ROTATION SCHEDULE

**Themes** (rotate in this order, never two consecutive the same):
1. Sales Techniques in Real Estate
2. Bali, Lombok & Surrounding Islands Real Estate Market
3. Legal Framework for Foreign Buyers in Indonesia
4. Construction Due Diligence in Bali

**Content Pillars** (rotate in this order):
1. The Educator — practical how-to content
2. The Perspective — contrarian takes
3. The Human — personal stories and client lessons
4. The Proof — data, results, case studies

---

## TROUBLESHOOTING

**No email received on Monday**
- Check your spam folder
- Go to Actions tab → check if the run completed with a green checkmark
- If the run failed (red X), click it to read the error log
- Most common cause: GMAIL_TOKEN has expired — redo Step 3 and update the secret

**"Authentication error" in the Actions log**
- Your GMAIL_TOKEN has expired
- Redo Step 3 (run authorize_gmail.py again) and update the GMAIL_TOKEN secret with the new token.json contents

**"Gemini API error" in the Actions log**
- Verify your GEMINI_API_KEY is correct
- Make sure it was generated from hello@scalrize.com (your Gemini Pro account)
- Check that your Gemini Pro subscription is still active at aistudio.google.com

**"Scraping failed" warning in the email**
- This is normal — LinkedIn blocks scrapers frequently
- The system automatically uses fallback news sources and still generates posts
- No action required

**GitHub Actions not running on Monday**
- GitHub occasionally delays scheduled workflows by up to 1 hour during high traffic
- If it never ran, check that the cron schedule in linkedin_poster.yml was not accidentally edited

**The workflow ran but no email arrived**
- The failure notification email should have arrived instead — check for that
- If neither email arrived, the GMAIL_TOKEN is likely the issue — update it

---

## FILE STRUCTURE

```
linkedin-automation/
├── main.py                    ← Master script (runs the full pipeline)
├── generate_post.py           ← Gemini AI post generation + validation
├── send_email.py              ← Gmail API email sender
├── scraper.py                 ← Firecrawl scraper + fallback sources
├── linkedin_prompt.md         ← Full AI prompt and content guidelines
├── requirements.txt           ← Python dependencies
├── post_log.txt               ← Rotation log (updated automatically)
├── authorize_gmail.py         ← One-time Gmail authorization script
├── README.md                  ← This file
└── .github/
    └── workflows/
        └── linkedin_poster.yml  ← GitHub Actions scheduler
```

---

## ACCOUNTS USED

| Service | Account |
|---|---|
| Gemini AI (post generation) | hello@scalrize.com |
| Gmail API (email sending) | matthieu.jammers@gmail.com |
| GitHub (automation hosting) | scalrize |
| Firecrawl (web scraping) | Your existing account |

---

## COST

- **GitHub Actions:** Free (well within the free tier limits)
- **Gemini AI:** Covered by your existing Gemini Pro subscription at hello@scalrize.com
- **Firecrawl:** Free tier (1 run per week uses minimal credits)
- **Gmail API:** Free

Total additional cost: **$0**

---

*This system runs entirely in the cloud. Your computer does not need to be on.*
