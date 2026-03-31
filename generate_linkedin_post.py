import os
import smtplib
import random
from datetime import date
from email.message import EmailMessage
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in .env file")
if not EMAIL_FROM or not EMAIL_TO or not EMAIL_APP_PASSWORD:
    raise ValueError("Email settings (EMAIL_FROM, EMAIL_TO, EMAIL_APP_PASSWORD) missing in .env file")

client = anthropic.Anthropic(api_key=API_KEY)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESUME_FILE = DATA_DIR / "resume.txt"
PROFILE_FILE = DATA_DIR / "linkedin_profile.txt"


def load_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"File is empty: {path}")
    return text


# 12 rotating post strategies — one fires each day, cycling with date as seed
POST_STRATEGIES = [
    {
        "name": "Achievement Story",
        "angle": (
            "Pick ONE specific accomplishment from their resume. Tell it as a mini-story: "
            "the challenge they faced, what they did differently, and the result with numbers if available. "
            "End with a lesson or takeaway that other professionals can relate to."
        ),
    },
    {
        "name": "Skill Deep Dive",
        "angle": (
            "Spotlight one technical skill or tool from their profile. Explain why mastering it changed how they work, "
            "share a real example of using it, and give one practical tip for others learning it. "
            "Position them as someone who truly understands the craft."
        ),
    },
    {
        "name": "Lessons Learned",
        "angle": (
            "Pull a lesson from their career journey — a mistake, a pivot, or something that surprised them. "
            "Be honest and human about what went wrong or what they didn't expect. "
            "Turn it into an insight that resonates with other professionals in their field."
        ),
    },
    {
        "name": "Hot Take / Contrarian View",
        "angle": (
            "Write a bold, slightly controversial opinion about their industry or role. "
            "Something that most people believe but the person's experience proves is wrong or overrated. "
            "Back it with their personal experience. Make it thought-provoking, not offensive. "
            "This drives comments and debate — high engagement."
        ),
    },
    {
        "name": "Career Journey",
        "angle": (
            "Tell the story of how they got to where they are today — the non-linear path, the unexpected turns, "
            "the moments of doubt, and what kept them going. "
            "Make it personal and authentic. End with where they're headed and what they're looking for next."
        ),
    },
    {
        "name": "Project Spotlight",
        "angle": (
            "Pick one project from their resume or profile and break it down: what problem it solved, "
            "the technical choices made, the challenges overcome, and the final result. "
            "Make it sound like a case study that shows depth of thinking, not just a list of features built."
        ),
    },
    {
        "name": "Industry Insight",
        "angle": (
            "Share an observation or trend in their industry based on their experience. "
            "Connect it to their day-to-day work and give a unique perspective that only someone in their role would have. "
            "Recruiters love candidates who think beyond their job description."
        ),
    },
    {
        "name": "Value Demonstration",
        "angle": (
            "Write a post that subtly demonstrates the candidate's value without being a resume recitation. "
            "Show how they think, how they solve problems, or how they approach their craft. "
            "Use a specific example or scenario. Let the quality speak for itself."
        ),
    },
    {
        "name": "Collaboration / Teamwork",
        "angle": (
            "Write about a time working with a great team, mentor, or colleague made all the difference. "
            "Celebrate the collaboration without making it all about them. "
            "Highlight what they contributed and what they learned. "
            "Recruiters love candidates who are self-aware and team-oriented."
        ),
    },
    {
        "name": "Resource / Tool Recommendation",
        "angle": (
            "Share 3-5 resources, tools, or habits that have genuinely helped them grow professionally. "
            "Make it specific to their field and experience level. Add personal commentary on why each one mattered. "
            "These posts get saved and shared heavily — great for reach."
        ),
    },
    {
        "name": "Open to Work Story",
        "angle": (
            "Write a human, confident, non-desperate job search post. "
            "Share what they've built, what they're proud of, what they're looking for next, "
            "and what kind of team or company they'd thrive in. "
            "Include a clear call to action. Make it magnetic, not a plea."
        ),
    },
    {
        "name": "Day in the Life",
        "angle": (
            "Write a 'Day in the life of a [their role]' post based on their actual experience. "
            "Make it specific, realistic, and relatable. Include the unglamorous parts too. "
            "This humanizes them and attracts recruiters who understand the role."
        ),
    },
]

# Rotate daily — same post type for the whole day, different each day
rng = random.Random(date.today().toordinal())
strategy = rng.choice(POST_STRATEGIES)

print(f"Today's post strategy: {strategy['name']}")

resume = load_file(RESUME_FILE)
profile = load_file(PROFILE_FILE)

prompt = f"""
You are a world-class LinkedIn ghostwriter and personal branding expert who has helped thousands of professionals land jobs at top companies. You write posts that get tens of thousands of views, hundreds of comments, and most importantly — make recruiters reach out.

Your job today: Write ONE exceptional LinkedIn post for this person based on their resume and LinkedIn profile below.

=== RESUME ===
{resume}

=== LINKEDIN PROFILE ===
{profile}

=== TODAY'S POST STRATEGY: {strategy['name']} ===
{strategy['angle']}

=== WRITING RULES (follow every single one) ===

HOOK (first 2 lines — make or break):
- The first line must stop the scroll. Use a bold statement, a surprising fact, a counterintuitive truth, or a relatable pain point.
- NO generic openers like "I'm excited to share", "Thrilled to announce", "I've been thinking about", or "Here's what I learned".
- The hook should make someone think "I need to read this."

BODY:
- Write in short punchy paragraphs — 1 to 3 lines max each.
- Use white space generously. LinkedIn rewards easy-to-read posts.
- Be specific. Use real numbers, real situations, real outcomes wherever possible.
- Write in first person. Sound like a real human, not a corporate bio.
- Keep a conversational, confident tone — not formal, not cringe-humble.

ENDING:
- End with a question to drive comments OR a strong CTA like "DM me if you're hiring" or "Save this for later."
- The last line should feel like a conclusion that lands — not just trail off.

EMOJIS:
- Use 3 to 6 emojis max. Place them naturally — not at the start of every line.
- Only use emojis that add meaning, not decoration.

HASHTAGS:
- Add 4 to 6 relevant hashtags at the very end on their own line.
- Mix broad (#SoftwareEngineering) and niche (#ReactDeveloper) tags.
- Match hashtags to the person's field and target audience.

LENGTH:
- 150 to 280 words for the post body (not counting hashtags).
- Long enough to deliver value, short enough to keep attention.

GOAL:
- This post must make a recruiter think: "I need to reach out to this person."
- It should feel authentic, not like a job ad or a press release.
- Every word should serve the goal of getting this person hired.

OUTPUT FORMAT:
Return ONLY the LinkedIn post — ready to copy and paste. No explanations, no "Here's the post:", no preamble. Just the post itself followed by the hashtags.
"""

print("Generating post with Claude Sonnet 4.5...")
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)

post_text = response.content[0].text.strip()

print("\n" + "=" * 60)
print("TODAY'S LINKEDIN POST")
print("=" * 60)
print(post_text)
print("=" * 60 + "\n")

# Send email
msg = EmailMessage()
msg["Subject"] = f"Your LinkedIn Post for Today — {strategy['name']} ({date.today().strftime('%B %d, %Y')})"
msg["From"] = EMAIL_FROM
msg["To"] = EMAIL_TO
msg.set_content(
    f"Here's your LinkedIn post for today ({strategy['name']} strategy).\n"
    f"Copy it, paste it on LinkedIn, and hit post!\n\n"
    f"{'=' * 60}\n\n"
    f"{post_text}\n\n"
    f"{'=' * 60}\n\n"
    f"Tips for maximum reach:\n"
    f"• Post between 8–10 AM or 12–1 PM on weekdays\n"
    f"• Reply to every comment within the first hour\n"
    f"• Don't edit the post after publishing (hurts reach)\n"
    f"• Like and comment on 5 posts before and after you post\n"
)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
    smtp.send_message(msg)

print(f"Post emailed to {EMAIL_TO}")
