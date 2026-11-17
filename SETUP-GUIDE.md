# EduTecJob: daily Instagram auto-post setup

This posts a **Question of the Day** to @edutecjob every morning at **9:00 AM IST** without you doing anything.
Each post has a quiz question, A/B/C/D options, yesterday's answer, and a call to visit edutecjob.com.
It runs free on GitHub, so your computer doesn't need to be on.

Setup takes about 30–45 minutes, once.

---

## Step 1: Make your Instagram a professional account
In the Instagram app, go to **Profile → ☰ Menu → Settings → Account type and tools → Switch to professional account**.
Choose **Business** (category: Education). If it's already a business account, skip this step.

## Step 2: Get your Instagram API key from Meta (official and free)
1. Go to **developers.facebook.com** and log in with Facebook. Click **My Apps → Create app**.
2. Choose the use case **"Manage messaging & content on Instagram"** and give the app a name, e.g. "EduTecJob Poster".
3. In the app, open **Instagram → API setup with Instagram login**.
4. Under **Generate access tokens**, click **Add account** and log in as **@edutecjob**.
   Allow the permissions it asks for (basic info and **content publishing**).
5. You'll now see two things there. Copy both and keep them private:
   - your **Instagram user ID** (a long number)
   - your **access token** (a long code). **Never share this in chat or with anyone.**

> The app can stay in "Development" mode. That's fine for posting to your own account.

## Step 3: Put this folder on GitHub (free)
1. Create a free account at **github.com**.
2. Click **+ → New repository**. Name it `edutecjob-autopost`, choose **Public**, and click **Create**.
   (It must be public so Instagram can fetch the images from it. Only the quiz questions are visible. Your keys stay secret.)
3. Click **uploading an existing file** and drag in: `make_post.py`, `post_to_instagram.py`, `questions.csv`, `SETUP-GUIDE.md`. Click **Commit changes**.
4. The schedule file lives in a hidden folder, so add it by hand:
   **Add file → Create new file**, type the name `.github/workflows/daily-post.yml`,
   paste in the contents of that file from this folder, then click **Commit changes**.

## Step 4: Add your keys as secrets
In the repository: **Settings → Secrets and variables → Actions → New repository secret**. Add two secrets:

| Name | Value |
|---|---|
| `IG_USER_ID` | the Instagram user ID from Step 2 |
| `IG_ACCESS_TOKEN` | the access token from Step 2 |

Secrets are encrypted. Nobody, including people who view the repository, can read them.

## Step 5: Test it
1. Open the **Actions** tab. If asked, click **"I understand my workflows, go ahead and enable them"**.
2. Click **Daily Instagram post → Run workflow**, tick **dry run**, then click **Run workflow**.
   After about a minute, the `published` folder has today's image. Open it to check it.
3. Run it again **without** ticking dry run. The post should appear on @edutecjob within a minute. 🎉

From then on, it posts **automatically every day at 9:00 AM**.

---

## Everyday use

**Add more questions:** open `questions.csv` on GitHub, click the ✏️ pencil, and add a line in the same format:
```
category,question,a,b,c,d,answer,explanation
```
(`answer` is A, B, C or D.) It comes with 30 questions. After the last one, it starts again from the first, so keep adding new ones. You can also edit the file in Excel or Google Sheets and save it as CSV.

**Change the posting time:** in `.github/workflows/daily-post.yml`, change `30 3 * * *`. The time is in UTC, which is IST minus 5:30. For example, `30 12 * * *` = 6:00 PM IST.

**Pause it:** go to **Actions → Daily Instagram post → ⋯ → Disable workflow**.

**If a post fails:** GitHub emails you. The same question is tried again the next day.

## ⚠️ Every ~50 days: renew the access token
Instagram tokens expire after 60 days. Before then, go back to developers.facebook.com, open
**Instagram → API setup with Instagram login**, and click **Generate token** again.
Then update the `IG_ACCESS_TOKEN` secret on GitHub (Step 4). Put a reminder in your calendar.
