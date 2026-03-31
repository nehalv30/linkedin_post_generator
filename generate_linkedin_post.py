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
# 15 topics drawn specifically from Nehal's real experience and domain.
# Generic topics have been removed — every topic is grounded in his actual work.

POST_TOPICS = [
    {
        "name": "The pipeline that lied",
        "angle": (
            "Write about the reality of data pipelines in production — they look clean until they don't. "
            "Draw from Nehal's experience building ingestion pipelines with Kafka, AWS Glue, and Redshift for fraud detection across 100+ banks. "
            "What does it actually take to trust your data? What breaks? What do most teams skip? "
            "Make this feel like hard-won knowledge, not a tutorial."
        ),
    },
    {
        "name": "Fraud detection is a data problem before it's a model problem",
        "angle": (
            "Nehal built fraud scoring data quality layers at Fiserv — standardizing 30+ JSON transaction attributes, "
            "writing 12 Python checks across millions of records. "
            "Most people think fraud detection is about ML models. The real bottleneck is almost always the data underneath. "
            "Write about this — what the data work actually looks like before a single model is trained."
        ),
    },
    {
        "name": "What working for Microsoft, Google, and Fiserv as a consultant taught me",
        "angle": (
            "Nehal supports multiple enterprise clients simultaneously through HCLTech. "
            "Each client (Fiserv = banking/fraud, Microsoft = enterprise tenants/M365, Google = chatbot analytics) has radically different data maturity. "
            "Write about what this cross-client view reveals — patterns in how good vs bad data teams operate, "
            "what enterprise clients actually need vs what they ask for, what most in-house analysts never see."
        ),
    },
    {
        "name": "The dashboard nobody uses",
        "angle": (
            "Nehal has built executive Power BI dashboards, Looker dashboards, Tableau dashboards. "
            "Most dashboards die. They get built, presented, and then nobody opens them again. "
            "Write about why this happens and how to build dashboards that people actually use. "
            "This should feel like a confession and a solution at the same time."
        ),
    },
    {
        "name": "Career path: DRDO → fintech → Universal Studios → HCLTech",
        "angle": (
            "Nehal's path is genuinely unusual: military cryptography research in India → fintech credit risk → "
            "theme park guest analytics in Orlando → senior consulting for Microsoft and Google in NYC. "
            "Write about what this non-linear path actually taught him — skills that transferred unexpectedly, "
            "moments of starting over, and why weird career paths often produce better analysts. "
            "Don't make it a resume recap. Make it a story."
        ),
    },
    {
        "name": "SQL is not a commodity skill",
        "angle": (
            "Everyone claims SQL on their resume. Very few people can actually model data well. "
            "Nehal has built star schemas in Azure Synapse, dbt fact/dimension tables, BigQuery UDFs, optimized Redshift tables. "
            "Write about the difference between knowing SQL syntax and actually understanding data modeling — "
            "what separates junior SQL from senior SQL in the real world."
        ),
    },
    {
        "name": "Saving 80 hours of manual QA with a Python script",
        "angle": (
            "Nehal automated financial data validation using Python checks integrated into Airflow pipelines, "
            "reducing data defects by ~50% and saving ~80 hours of manual QA per month. "
            "Write about this specifically — what the manual process looked like, what the automation actually did, "
            "and the broader lesson about where automation creates the most leverage in data work."
        ),
    },
    {
        "name": "What I saw analyzing 15 years of theme park data at Universal Studios",
        "angle": (
            "Nehal analyzed 15 years of park attendance, ride throughput, and guest survey data at Universal Orlando. "
            "This is genuinely interesting — the patterns in crowd behavior, peak traffic, ride preferences. "
            "Write about one surprising insight from this work (invent a plausible one grounded in the domain). "
            "Frame it as: 'here's what 15 years of data says about how people behave' — "
            "everyone loves data stories about places they've been."
        ),
    },
    {
        "name": "The honest job search post",
        "angle": (
            "Write a confident, magnetic, non-desperate open-to-work post for Nehal. "
            "Not 'I'm looking for opportunities' energy — more like 'here's exactly what I've built and what I want next.' "
            "Include specific things he's proud of, the type of team he thrives in, and a clear CTA. "
            "Should make a recruiter at Stripe, Snowflake, or a fintech feel like they'd be lucky to have him."
        ),
    },
    {
        "name": "dbt changed how I think about data — but not in the way you'd expect",
        "angle": (
            "Nehal builds dbt models with incremental loads, data quality tests, and fact/dimension tables for banking clients. "
            "Write about what working with dbt at scale actually revealed — not the marketing pitch, "
            "but the real lessons about data modeling, team collaboration, and where dbt genuinely helps vs where it creates new problems. "
            "Give the honest take."
        ),
    },
    {
        "name": "From 2 million transactions a day to zero trust in the data",
        "angle": (
            "At Rapipay, Nehal engineered pipelines processing 2M+ daily financial transactions using Hadoop, Spark, Hive, HBase. "
            "Write about what operating at that scale teaches you about data reliability — "
            "the silent failures, the aggregations that lie, the moment you realize your 'clean' data isn't. "
            "Make it visceral and specific."
        ),
    },
    {
        "name": "Power BI vs Tableau — I've used both for years. Here's my real take.",
        "angle": (
            "Nehal has used both Power BI and Tableau extensively across clients. "
            "Write a sharp, opinionated comparison — not a feature list, but when each one actually wins, "
            "which one enterprise clients default to and why, and which one produces better insights in practice. "
            "Be specific and willing to pick a side."
        ),
    },
    {
        "name": "What RNN-based cryptography research taught me about data quality",
        "angle": (
            "At DRDO, Nehal built an RNN model to validate AES and PICO encryption on military data — achieving 95% accuracy. "
            "This is a genuinely unusual experience. Write about what working with highly sensitive, high-stakes data taught him "
            "about data integrity, validation, and what 'good enough' means when the consequences are real. "
            "Connect it to what he does now in financial data."
        ),
    },
    {
        "name": "The metric nobody tracks but should",
        "angle": (
            "Based on Nehal's experience across banking, enterprise SaaS, and consumer analytics — "
            "write about one underrated metric or measurement that most data teams ignore but that reveals a huge amount. "
            "Could be about pipeline freshness, dashboard engagement, data team ROI, or something domain-specific. "
            "Make it feel like insider knowledge from someone who's seen a lot of dashboards."
        ),
    },
    {
        "name": "Masters in Business Analytics — was it worth it?",
        "angle": (
            "Nehal did a Master's in Business Analytics at Northeastern University, moving from India to the US. "
            "Write an honest take on the MBA/MSBA question — what he actually learned vs what he expected, "
            "what the degree opened up, what he wishes he'd done differently, and whether he'd recommend it. "
            "Keep it honest — not a Northeastern ad, not a 'degrees are useless' take either. Just real."
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
