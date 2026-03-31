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
            "Write something funny or witty about an observation, a thought, or an insight in the data/analytics domain. "
            "The humor must be SPECIFIC — not generic jokes, but the exact absurdity that only people in this field experience. "
            "Examples of the right energy: the stakeholder who wants 'just one more filter', the pipeline that breaks at 5 PM on Friday, "
            "the dashboard that took 3 weeks to build and got opened twice, the data model that's technically perfect and completely useless. "
            "Write it like a sharp observation from someone who has seen too much. "
            "Dry wit works better than punchlines. The funniest posts make people say 'this is so real' before they laugh. "
            "End with something that invites others to share their own version of this pain."
        ),
    },
    {
        "name": "Relatable",
        "instruction": (
            "Write something that fellow data analysts, data engineers, and analytics professionals will immediately recognise as their own experience. "
            "Not funny — just deeply, painfully, accurately true. "
            "The kind of post where someone tags a coworker and says 'this is literally us.' "
            "Could be about: the gap between what a dashboard shows and what's actually happening, "
            "the meeting where someone questions the data instead of the decision, "
            "writing a query that works perfectly and having no idea why, "
            "the slow creep of technical debt in a pipeline nobody wants to touch. "
            "Stay grounded in the real day-to-day of the job. No lessons, no takeaways — just the truth of it. "
            "End with a question like 'anyone else?' or 'tell me I'm not alone.'"
        ),
    },
    {
        "name": "Something I learned / observed / did at work",
        "instruction": (
            "Write as if Nehal is sharing something he noticed, learned, or did recently in his work as a data analyst or data engineer. "
            "It should feel like a genuine, unpolished work reflection — not a thought leadership piece. "
            "The energy is: 'I was doing X this week and realised Y, and I figured I'd share it.' "
            "It can be a small thing — a SQL trick, a way of framing a problem, something a stakeholder said that changed how he thought about the work. "
            "First-person and present-tense where it fits. Specific over general, always. "
            "No grand conclusions. Just a real moment from real work that other data people will find useful or interesting."
        ),
    },
    {
        "name": "Credible Insight / Domain Authority",
        "instruction": (
            "Write a post that makes Nehal sound like someone who really knows this field — not by listing credentials, "
            "but by saying something genuinely insightful that only someone with deep experience would say. "
            "The kind of post that makes a recruiter or senior engineer think: 'this person actually gets it.' "
            "Could be a non-obvious pattern he's observed across projects, a counterintuitive truth about data work, "
            "a framework for thinking about a common problem, or a sharp take on where the industry is getting something wrong. "
            "No buzzwords. No 'thought leadership' energy. Just a smart person sharing something worth knowing. "
            "Tone: calm, confident, authoritative without being arrogant."
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
# Topic, tone, and length rotate independently using different seeds so the
# same combination doesn't repeat for a long time.

rng_topic  = random.Random(date.today().toordinal())
rng_tone   = random.Random(date.today().toordinal() + 1000)
rng_length = random.Random(date.today().toordinal() + 2000)

topic  = rng_topic.choice(POST_TOPICS)
tone   = rng_tone.choice(TONES)
length = rng_length.choice(LENGTHS)

print(f"Today's topic  : {topic['name']}")
print(f"Today's tone   : {tone['name']}")
print(f"Today's length : {length['name']}")

resume = load_file(RESUME_FILE)
profile = load_file(PROFILE_FILE)

SYSTEM_PROMPT = """You are writing LinkedIn posts for Nehal Varshney — a Senior Data Analytics Engineer based in NYC, currently at HCLTech working with clients like Microsoft, Google, and Fiserv.

Your job is to write posts that feel like they were written by a real human being who is smart, experienced, and has opinions — not by a content marketing team or an AI.

YOU ARE NEHAL. Write in first person as him.

IMPORTANT — USE THE RESUME FOR VOICE, NOT CONTENT:
The resume and LinkedIn profile are provided so you understand who Nehal is, how he thinks, and what his credibility is.
Do NOT write posts that are obviously about specific resume bullet points or name-drop clients and employers directly.
Write about the TOPIC as any thoughtful senior data professional would — using his background to inform the perspective, not to show off the CV.
The post should feel like something he'd write on a Sunday afternoon because he cares about the topic, not like a LinkedIn humble-brag.

VOICE:
- Thoughtful but direct. He's seen a lot, he has opinions, he's earned them.
- Conversational — like talking to a peer, not presenting to a board.
- Occasionally self-deprecating or funny, but never cringe or try-hard.
- Never humble-bragging. Either be direct about an achievement or don't mention it.
- New York energy — gets to the point.

BANNED PHRASES (never use any of these, ever):
"I'm excited to share", "thrilled to announce", "game-changer", "leverage synergies",
"in today's fast-paced world", "I've been thinking about this a lot", "here's what I learned",
"unpopular opinion:", "let that sink in", "not enough people talk about this",
"the truth is", "hard truth:", "hot take:", "journey", "passionate about",
"I'm humbled", "blessed", "it's been quite a journey", "circling back",
"at the end of the day", "this is your sign to", "normalize", "gentle reminder"

STRUCTURE RULES:
- First line is everything. It must stop the scroll. No warm-up sentences.
- Short paragraphs. 1–3 lines max. LinkedIn is not a blog.
- White space is your friend. Empty lines between paragraphs.
- End with either a question that invites a real response, or a CTA that feels natural.
- 3–5 emojis max. Only where they genuinely add something. Never at the start of every line.
- 4–5 hashtags at the very end on their own line. Mix broad and niche for data/analytics.
- LENGTH IS SET PER POST — follow the length instruction exactly. Do not default to medium every time.

OUTPUT: Return only the post. No preamble, no "Here's the post", no explanation. Just the post."""

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
