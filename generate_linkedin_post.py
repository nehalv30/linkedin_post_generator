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


# ─── TONES ────────────────────────────────────────────────────────────────────
# Each post gets a TOPIC + a TONE. They rotate independently so the same topic
# never hits twice in the same emotional register.

TONES = [
    {
        "name": "Useful / Teach something",
        "instruction": (
            "This post should genuinely teach the reader something they can use. "
            "Make it specific — not 'SQL is important' but 'here is the exact pattern most analysts get wrong in SQL and why.' "
            "Think: someone reads this and immediately learns one thing they didn't know before. "
            "Tone is confident, clear, zero fluff. Like a smart colleague explaining something at a whiteboard."
        ),
    },
    {
        "name": "Hot Take / Contrarian",
        "instruction": (
            "Write a bold opinion that goes against what most people in data/analytics believe. "
            "Something that will make half the readers nod and half want to argue in the comments. "
            "Back it with a real observation from Nehal's experience. "
            "Tone is direct and unapologetic — not rude, but not hedging either. "
            "Example energy: 'Everyone talks about dbt. Nobody talks about the 80% of problems dbt creates downstream.' "
            "This is the tone. Match it to the topic."
        ),
    },
    {
        "name": "Funny / Relatable",
        "instruction": (
            "Write something that makes data professionals laugh because it's painfully true. "
            "The humor comes from specificity — not generic jokes, but the exact absurdity of real analytics work. "
            "Think: a dashboard that nobody used, a pipeline that broke Friday at 5 PM, a stakeholder asking to 'just add one more filter.' "
            "Keep it light and self-aware. The post should feel like a tweet that accidentally went viral. "
            "End with something that invites people to share their own horror stories."
        ),
    },
    {
        "name": "Personal / Story",
        "instruction": (
            "Write a personal story from Nehal's career — a real moment of doubt, failure, unexpected win, or turning point. "
            "The non-linear path (DRDO → fintech → theme parks → consulting for Microsoft/Google) is gold — use it. "
            "Make the reader feel something. Vulnerability is strength here. "
            "The lesson should emerge naturally from the story — never state it as a moral. "
            "Tone: warm, honest, human. Like a conversation over coffee, not a TED talk."
        ),
    },
    {
        "name": "Practical / Tactical",
        "instruction": (
            "Write a numbered or structured post that gives the reader a framework, checklist, or process they can apply immediately. "
            "Based on something Nehal actually does — how he approaches data quality, pipeline design, stakeholder reporting, fraud detection, etc. "
            "Make it feel like insider knowledge, not a textbook. "
            "Tone: efficient and direct. Every line earns its place. "
            "This type gets saved and shared — optimize for that."
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
# Use date as seed so the combo is consistent within a day but rotates daily.
# Topics and tones rotate independently — same topic won't get the same tone
# for a long time, keeping the feed varied.

rng = random.Random(date.today().toordinal())
topic = rng.choice(POST_TOPICS)
tone = rng.choice(TONES)

print(f"Today's topic : {topic['name']}")
print(f"Today's tone  : {tone['name']}")

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
- 3–6 emojis max, placed where they add meaning not decoration.
- 4–6 hashtags at the very end, mix of broad and niche for his field.
- 150–280 words in the post body (not counting hashtags).

OUTPUT: Return only the post. No preamble, no "Here's the post", no explanation. Just the post."""

USER_PROMPT = f"""=== NEHAL'S RESUME ===
{resume}

=== NEHAL'S LINKEDIN PROFILE ===
{profile}

=== TODAY'S TOPIC: {topic['name']} ===
{topic['angle']}

=== TODAY'S TONE: {tone['name']} ===
{tone['instruction']}

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
print(f"TODAY'S LINKEDIN POST  [{tone['name']}]")
print("=" * 60)
print(post_text)
print("=" * 60 + "\n")

# Send email
msg = EmailMessage()
msg["Subject"] = (
    f"LinkedIn Post — {topic['name']} [{tone['name']}] · {date.today().strftime('%b %d, %Y')}"
)
msg["From"] = EMAIL_FROM
msg["To"] = EMAIL_TO
msg.set_content(
    f"Topic  : {topic['name']}\n"
    f"Tone   : {tone['name']}\n"
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
