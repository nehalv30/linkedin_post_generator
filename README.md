# LinkedIn Post Generator

AI-powered daily LinkedIn post generator. Reads your resume and LinkedIn profile, crafts a recruiter-attracting post every day, and emails it to you ready to copy-paste.

## Setup

### 1. Add your resume and profile

Fill in these two files with your actual content:
- `data/resume.txt` — paste your full resume as plain text
- `data/linkedin_profile.txt` — paste your LinkedIn headline, About section, skills, etc.

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=   # Get from https://console.anthropic.com/
EMAIL_FROM=          # Your Gmail address
EMAIL_TO=            # Where to send the posts (can be the same Gmail)
EMAIL_APP_PASSWORD=  # Gmail App Password (not your regular password)
```

**Gmail App Password:** Go to myaccount.google.com → Security → 2-Step Verification → App Passwords → create one for "Mail".

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run manually

```bash
python generate_linkedin_post.py
```

### 5. Schedule to run daily (optional)

**Mac/Linux (cron):**
```bash
crontab -e
# Add this line to run every day at 8 AM:
0 8 * * * cd /path/to/linkedin-post-generator && python generate_linkedin_post.py
```

**Windows (Task Scheduler):** Create a basic task that runs `python generate_linkedin_post.py` daily.

## How it works

- Rotates through **12 different post strategies** (Achievement Story, Hot Take, Career Journey, Skill Deep Dive, etc.)
- A different strategy fires each day based on the date — no repeats for 12 days
- Uses Gemini to write in your voice based on your resume and profile
- Sends the finished post to your email with copy-paste formatting and posting tips

## Post Strategies

1. Achievement Story
2. Skill Deep Dive
3. Lessons Learned
4. Hot Take / Contrarian View
5. Career Journey
6. Project Spotlight
7. Industry Insight
8. Value Demonstration
9. Collaboration / Teamwork
10. Resource / Tool Recommendation
11. Open to Work Story
12. Day in the Life
