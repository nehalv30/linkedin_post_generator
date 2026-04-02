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


# ─── LENGTHS ──────────────────────────────────────────────────────────────────
# Rotates independently so the feed has natural variety — not every post is
# the same length.

LENGTHS = [
    {
        "name": "Short",
        "instruction": (
            "Write a SHORT post: 60–100 words max, not counting hashtags. "
            "One sharp idea, fully expressed. No fluff, no build-up. "
            "Think of it like a really good tweet that deserved more space. "
            "Every single sentence must earn its place. If a line can be cut, cut it."
        ),
    },
    {
        "name": "Medium",
        "instruction": (
            "Write a MEDIUM post: 130–200 words, not counting hashtags. "
            "Enough room for a setup, a point, and a landing. "
            "Don't pad it out — stop as soon as the idea is complete."
        ),
    },
    {
        "name": "Long",
        "instruction": (
            "Write a LONG post: 250–350 words, not counting hashtags. "
            "This can be a story, a structured breakdown, or a deep observation. "
            "Use the length to go deeper — not to repeat yourself. "
            "Short paragraphs throughout. The extra length should feel earned, not padded."
        ),
    },
]


# ─── TONES ────────────────────────────────────────────────────────────────────
# 4 tones as specified. Rotate independently from topic and length.

TONES = [
    {
        "name": "Funny / Witty",
        "instruction": (
            "Write something funny or witty about an observation or frustration in data/analytics work. "
            "The humor has to be specific. Not 'data is messy lol' but the exact particular absurdity that people in this field live with. "
            "Think: the stakeholder who wants just one more filter after the dashboard is already live. "
            "The pipeline that picks Friday at 5pm to break. "
            "The data model that is technically beautiful and practically ignored. "
            "The report that everyone requests and nobody reads. "
            "Write it like Nehal is venting to a friend who works in the same field. Dry, a little tired, accurate. "
            "Do not try to land a punchline. The funny comes from how precisely true it is. "
            "Maybe end by asking if anyone else has been in this exact situation."
        ),
    },
    {
        "name": "Relatable",
        "instruction": (
            "Write something that data people will read and immediately feel seen. "
            "Not funny, not insightful. Just true in a way that makes someone stop scrolling. "
            "The kind of post where a person tags their coworker and says nothing except their name. "
            "Could be about the meeting where someone challenges the data instead of the decision it supports. "
            "Or writing a query that somehow works and having no idea why and not touching it again. "
            "Or the pipeline that has been 'good enough' for two years and everyone is too scared to refactor. "
            "No lesson. No takeaway. No wrap-up. Just the observation, stated plainly. "
            "If it ends with a question, make it feel natural, like 'anyone else deal with this?' not a forced engagement hook."
        ),
    },
    {
        "name": "Something I learned / observed / did at work",
        "instruction": (
            "Write as if Nehal is sharing something real from his week at work. "
            "Not a lecture. More like a message to a group chat of colleagues. "
            "The energy is: I was doing something, I noticed something, I figured I would write it down. "
            "It can be small. A SQL pattern that tripped him up. A way of explaining something to a stakeholder that actually worked. "
            "Something he built that did or did not work the way he expected. "
            "Write in present tense where it fits. Keep it grounded in the actual work, not in abstract advice. "
            "Do not wrap it up with a lesson. End where the thought ends."
        ),
    },
    {
        "name": "Credible Insight / Domain Authority",
        "instruction": (
            "Write something that makes Nehal sound like someone who has actually been in the room when these things happen. "
            "Not credential-dropping. Not thought leadership. Just a sharp observation that someone with real experience would make. "
            "The kind of thing a senior person says in a meeting that makes everyone else go quiet for a second. "
            "It could be a pattern he keeps seeing across different companies. "
            "A common assumption in the field that is wrong in a specific way. "
            "A thing everyone does that quietly causes problems nobody wants to name. "
            "Tone is calm and matter-of-fact. Not trying to impress anyone. Just saying what he sees. "
            "No buzzwords. No big conclusions. Just the observation, stated with confidence."
        ),
    },
]


# ─── TOPICS ───────────────────────────────────────────────────────────────────
# Domain topics for a senior data/analytics professional.
# NOT resume bullet points — these are things a smart person in this field
# would organically post about. The resume is only used for voice + credibility.

POST_TOPICS = [
    {
        "name": "Why most data pipelines fail silently",
        "angle": (
            "The scariest data bugs aren't the ones that crash — they're the ones that pass silently and corrupt downstream. "
            "Write about why silent pipeline failures are so common, what patterns cause them, "
            "and the practical things you can do to actually catch them before a stakeholder does. "
            "Keep it specific to real pipeline work — Kafka, Airflow, batch jobs, whatever fits naturally."
        ),
    },
    {
        "name": "The problem with how companies hire data people",
        "angle": (
            "Most data job interviews test the wrong things. LeetCode SQL puzzles don't predict whether someone can "
            "actually model a business problem or communicate findings to a non-technical team. "
            "Write a sharp take on what the data hiring process gets wrong and what good hiring actually looks like. "
            "Be specific. Be willing to name the dysfunction."
        ),
    },
    {
        "name": "Everyone says they're data-driven. Almost nobody is.",
        "angle": (
            "Companies love saying they're data-driven. In practice, most decisions still get made on gut feel "
            "and the data gets used to justify the conclusion that was already reached. "
            "Write an honest post about what actually blocks data-driven culture — "
            "not tools, not talent, but the organizational patterns that make data decorative."
        ),
    },
    {
        "name": "SQL patterns most analysts get wrong",
        "angle": (
            "Pick one or two SQL patterns that look correct but produce subtly wrong results — "
            "things like NULL handling in aggregations, window function frame defaults, JOIN behavior with duplicates, "
            "or COUNT(*) vs COUNT(col). Write it as a practical teaching post with a concrete example. "
            "Make it feel like something you wish someone had told you earlier."
        ),
    },
    {
        "name": "Dashboards don't drive decisions — here's what does",
        "angle": (
            "Most dashboards get built, get presented, and then quietly die. "
            "The reason isn't the tool. It's that dashboards answer questions nobody was asking, "
            "or answer them too late, or require too much interpretation. "
            "Write about what actually drives decisions in organizations and how analytics can plug into that. "
            "Give people something they can change on Monday morning."
        ),
    },
    {
        "name": "The real difference between a junior and senior data analyst",
        "angle": (
            "It's not SQL speed. It's not Python. It's not the number of tools on the resume. "
            "Write about what actually separates junior from senior in data work — "
            "how they frame problems, handle ambiguity, communicate uncertainty, push back on bad requests. "
            "Make it concrete. Give examples of junior behavior vs senior behavior on the same situation."
        ),
    },
    {
        "name": "Hot take on dbt",
        "angle": (
            "dbt has become the default for analytics engineering. "
            "Write an honest, opinionated take on it — what it genuinely solves, where the hype outpaces the reality, "
            "what problems it creates that people don't talk about. "
            "Not a hit piece, not a fan post — a real take from someone who has used it in production."
        ),
    },
    {
        "name": "What Snowflake, Databricks, and BigQuery don't tell you",
        "angle": (
            "The modern data stack has incredible marketing. The gap between the demo and production reality is enormous. "
            "Write about the things you only learn after actually running a data warehouse at scale — "
            "cost surprises, performance gotchas, the stuff the documentation buries. "
            "Be specific and practical. This is the post someone saves for when they're about to make a vendor decision."
        ),
    },
    {
        "name": "Python for data analysts — what to actually learn",
        "angle": (
            "Everyone tells analysts to learn Python. Almost nobody tells them what to actually focus on. "
            "Write a clear, opinionated guide on the Python skills that actually matter for data work — "
            "and explicitly call out the things that are overhyped or irrelevant for most analysts. "
            "Make it actionable enough that someone can start this weekend."
        ),
    },
    {
        "name": "The data quality problem nobody wants to own",
        "angle": (
            "Data quality is everyone's problem and nobody's responsibility. "
            "Engineering says it's analytics' job. Analytics says it's engineering's job. "
            "The business doesn't care whose job it is — they just see wrong numbers in the report. "
            "Write about how this dynamic plays out and what actually fixes it. "
            "Be direct about the organizational reality, not just the technical solution."
        ),
    },
    {
        "name": "When ML makes things worse",
        "angle": (
            "Machine learning gets applied to problems where a simple rule or a SQL query would do the job better. "
            "Write about the situations where ML is the wrong call — overcomplicated, opaque, expensive to maintain, "
            "and worse than a well-thought-out heuristic. "
            "This isn't an anti-ML post — it's a pro-thinking post. When should you not reach for the model?"
        ),
    },
    {
        "name": "What fintech data actually looks like",
        "angle": (
            "People outside fintech imagine clean transaction tables. "
            "The reality is nested JSON, inconsistent schemas across banks, missing fields, duplicate events, "
            "and timing issues that make aggregations lie. "
            "Write about what financial data is really like in the wild — the mess, the edge cases, the gotchas — "
            "and how to actually work with it reliably."
        ),
    },
    {
        "name": "Airflow is not the answer to your pipeline problems",
        "angle": (
            "Airflow gets adopted as the solution to messy pipelines. "
            "Often it just turns messy pipelines into messy Airflow DAGs. "
            "Write about what Airflow actually solves, where teams misuse it, "
            "and what questions you should ask before reaching for an orchestration tool. "
            "Practical and specific — for people who have felt this pain."
        ),
    },
    {
        "name": "The metric that actually tells you if your data team is working",
        "angle": (
            "Most data teams track output: dashboards shipped, queries written, models deployed. "
            "None of those measure whether the data team is actually useful to the business. "
            "Write about what metrics or signals actually indicate a healthy, impactful data function — "
            "things you can observe without a big measurement framework."
        ),
    },
    {
        "name": "Moving from India to the US for a data career",
        "angle": (
            "Write an honest post about what the transition is actually like — "
            "the gap between what you expect and what the job market, culture, and day-to-day work actually look like. "
            "What skills transferred well? What had to be relearned? What would you tell someone considering the same move? "
            "Keep it grounded and real — not a success story, not a warning. Just the truth."
        ),
    },
    {
        "name": "Kafka is overkill for most companies",
        "angle": (
            "Real-time streaming is exciting to build and often unnecessary to run. "
            "Write about when Kafka (or any streaming infrastructure) is genuinely the right call "
            "vs when a well-designed batch job would do the same job at a fraction of the complexity. "
            "Give people a framework for making this call, not just an opinion."
        ),
    },
    {
        "name": "What good stakeholder communication looks like in data roles",
        "angle": (
            "Most data training is technical. The skill that actually determines career growth is communication — "
            "knowing how to present uncertainty, push back on bad requests, translate findings for non-technical audiences, "
            "and manage expectations when the data doesn't have a clean answer. "
            "Write about what this looks like in practice. Give concrete examples."
        ),
    },
    {
        "name": "The honest take on Azure vs AWS vs GCP for data",
        "angle": (
            "Every cloud has a different strengths story. The real differences only show up when you've used them. "
            "Write an opinionated but fair comparison of the three for data workloads specifically — "
            "not a feature matrix, but actual working experience: "
            "which ecosystem is most mature, where the pricing gets you, what the developer experience is actually like."
        ),
    },
    {
        "name": "Stop building data models nobody asked for",
        "angle": (
            "Analytics engineers love clean, well-modeled data. Business stakeholders love answers to their questions. "
            "These are not always the same thing. "
            "Write about the trap of over-engineering data models that are technically beautiful and practically unused — "
            "and how to stay connected to what the business actually needs. "
            "Be direct about where the disconnect usually comes from."
        ),
    },
    {
        "name": "What I'd do differently if I started my data career today",
        "angle": (
            "Write a reflective, practical post about what a person entering data today should prioritize — "
            "and what most people waste time on. "
            "Not another 'learn Python and SQL' post — go deeper. "
            "What mental models, habits, or skills would actually compound over a career? "
            "Make it feel like advice from someone a few years ahead, not a course ad."
        ),
    },
]


# ─── DAILY SELECTION ──────────────────────────────────────────────────────────
# Use day index to cycle through topics/tones/lengths in order so nothing
# repeats until the full list is exhausted. Topics cycle every 20 days,
# tones every 4, lengths every 3 — all out of phase so combinations stay fresh.

day_index = date.today().toordinal()

# Shuffle each list with a fixed seed so the order is consistent but not obvious
topic_order  = random.Random(42).sample(range(len(POST_TOPICS)), len(POST_TOPICS))
tone_order   = random.Random(43).sample(range(len(TONES)), len(TONES))
length_order = random.Random(44).sample(range(len(LENGTHS)), len(LENGTHS))

topic  = POST_TOPICS[topic_order[day_index % len(POST_TOPICS)]]
tone   = TONES[tone_order[day_index % len(TONES)]]
length = LENGTHS[length_order[day_index % len(LENGTHS)]]

print(f"Today's topic  : {topic['name']}")
print(f"Today's tone   : {tone['name']}")
print(f"Today's length : {length['name']}")

resume = load_file(RESUME_FILE)
profile = load_file(PROFILE_FILE)

SYSTEM_PROMPT = """You are writing LinkedIn posts for Nehal Varshney. He is a Senior Data Analytics Engineer living in NYC, originally from India, currently at HCLTech working across clients in banking, enterprise tech, and consumer analytics.

You are not a ghostwriter producing polished content. You are Nehal typing a post himself. Write exactly like that.

WHO NEHAL IS:
He is smart, a bit dry, occasionally self-deprecating. He has worked across enough industries to have real opinions. He does not perform enthusiasm. He does not write like he is trying to build a personal brand. He writes like someone who noticed something, or got mildly annoyed at something, or figured something out, and decided to say it out loud.

He grew up in India, did his undergrad in computer engineering, moved to the US for his master's at Northeastern, and has been in NYC for a few years now. That background shows up subtly in how he talks: he is not trying to sound American, he is not trying to sound formal, he just sounds like himself.

He works in data. He genuinely finds it interesting. He also finds it frustrating in specific ways that anyone in the field would recognise.

VOICE:
Write the way a smart person actually types, not the way a copywriter would write it for them. That means:
- Sentences can be short and blunt. Or they can run on a bit when the thought needs it.
- Starting a sentence with "And" or "But" or "So" is fine. People do that.
- Contractions always. "it's", "don't", "I've", "you're". Never "it is" or "do not" unless it's for emphasis.
- Casual but not sloppy. He is not dumbing it down. He is just not performing.
- Occasionally a little dry or wry. Not trying to be funny. Just honest in a way that happens to be a bit funny.
- Sometimes he will include a small personal detail or observation that makes the post feel lived-in. Not a story with a lesson. Just a moment.

PUNCTUATION RULES (critical):
- NO em dashes. Not a single one. (— this character is banned completely)
- NO en dashes used as separators. (– also banned)
- If you would use a dash, use a comma, a period, or just start a new sentence instead.
- Colons are fine when listing something. Parentheses are fine for an aside. Full stops are your best friend.
- Do not use ellipses (...) for dramatic effect. Either say the thing or don't.

BANNED PHRASES (do not write any of these under any circumstances):
"I'm excited to share", "thrilled to announce", "game-changer", "leverage synergies",
"in today's world", "I've been thinking about this", "here's what I learned",
"unpopular opinion:", "let that sink in", "not enough people talk about this",
"the truth is", "hard truth:", "hot take:", "journey", "passionate about",
"I'm humbled", "blessed", "circling back", "at the end of the day",
"this is your sign", "normalize", "gentle reminder", "it's giving",
"as someone who", "I wanted to share", "just a reminder", "deep dive"

DO NOT:
- Use bullet points formatted as "1. Thing\n2. Thing" unless the post specifically calls for a list
- Write a moral at the end of every post. Sometimes the observation IS the point.
- Over-explain the insight. Trust the reader.
- Use adjectives like "powerful", "amazing", "incredible", "crucial", "essential"
- End every post with a question. Only ask one if it genuinely invites a response.

STRUCTURE:
- First line stops the scroll. No warm-up. No context-setting. Start in the middle of the thought.
- Short paragraphs. One idea per paragraph. Empty line between each.
- 2 to 4 emojis at most. Only if they add something. Not as decoration.
- 4 to 5 hashtags at the very end on their own line.
- LENGTH comes from the length instruction. Follow it exactly.

OUTPUT: Return only the post. Nothing else. No "Here is the post", no explanation. Just the post itself."""

USER_PROMPT = f"""=== NEHAL'S RESUME ===
{resume}

=== NEHAL'S LINKEDIN PROFILE ===
{profile}

=== TODAY'S TOPIC: {topic['name']} ===
{topic['angle']}

=== TODAY'S TONE: {tone['name']} ===
{tone['instruction']}

=== TODAY'S LENGTH: {length['name']} ===
{length['instruction']}

Write the post now."""

print("Generating post with Claude Sonnet 4.5...")
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": USER_PROMPT}],
)

post_text = response.content[0].text.strip()

print("\n" + "=" * 60)
print(f"TODAY'S LINKEDIN POST  [{length['name']} · {tone['name']}]")
print("=" * 60)
print(post_text)
print("=" * 60 + "\n")

# Send email
msg = EmailMessage()
msg["Subject"] = (
    f"LinkedIn Post — {topic['name']} [{length['name']} · {tone['name']}] · {date.today().strftime('%b %d, %Y')}"
)
msg["From"] = EMAIL_FROM
msg["To"] = EMAIL_TO
msg.set_content(
    f"Topic  : {topic['name']}\n"
    f"Tone   : {tone['name']}\n"
    f"Length : {length['name']}\n"
    f"Date   : {date.today().strftime('%B %d, %Y')}\n\n"
    f"{'─' * 60}\n\n"
    f"{post_text}\n\n"
    f"{'─' * 60}\n\n"
    f"POSTING TIPS:\n"
    f"• Best times: 8–10 AM or 12–1 PM on Tue/Wed/Thu\n"
    f"• Reply to every comment in the first 60 minutes (big reach boost)\n"
    f"• Don't edit the post after publishing — it tanks the algorithm\n"
    f"• Engage on 5–10 posts right before you publish\n"
    f"• If it's getting traction, pin it to your profile\n"
)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
    smtp.send_message(msg)

print(f"Post emailed to {EMAIL_TO}")

# Write to post log so GitHub sees repo activity every day (keeps scheduled workflow reliable)
LOG_FILE = BASE_DIR / "logs" / "posts.md"
LOG_FILE.parent.mkdir(exist_ok=True)

log_entry = (
    f"## {date.today().strftime('%B %d, %Y')}\n"
    f"**Topic:** {topic['name']}\n"
    f"**Tone:** {tone['name']} | **Length:** {length['name']}\n\n"
    f"{post_text}\n\n"
    f"---\n\n"
)

existing = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else ""
LOG_FILE.write_text(log_entry + existing, encoding="utf-8")
print(f"Post logged to {LOG_FILE}")
