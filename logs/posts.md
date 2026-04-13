## April 13, 2026
**Topic:** What I'd do differently if I started my data career today
**Tone:** Something I learned / observed / did at work | **Length:** Medium

I've been doing this for a few years now and if I had to start over, I wouldn't touch a tutorial for the first month.

I'd find one dataset. Something real. Maybe public transit data, restaurant inspections, anything messy. And I'd just try to answer questions nobody asked me to answer.

How many inspections failed in winter vs summer? Which neighborhoods had the weirdest patterns? What happens if I group this five different ways?

Most people learn syntax. That's fine. But the real skill is knowing what question to ask next. And you can't learn that from a course. You learn it by staring at data until something looks off, then figuring out why.

I've worked with people who can write perfect SQL but freeze when you ask them what's actually worth measuring. And I've worked with people who barely know pandas but always seem to find the one thing that matters.

The second group gets promoted faster.

#DataAnalytics #DataScience #CareerAdvice #SQL #Python

---

## April 10, 2026
**Topic:** Dashboards don't drive decisions — here's what does
**Tone:** Funny / Witty | **Length:** Medium

You know what's wild?

Every team I've worked with has at least one dashboard that took three weeks to build, got presented in a big meeting, and was never opened again.

It has everything. Filters by region, product, time period. Three different chart types. A calculated field that took two days to get right.

Nobody uses it.

Because the VP still makes decisions based on the conversation they had with a customer last week. Or the thing their friend at another company is doing. Or just vibes.

The dashboards that actually matter? They're the ones someone checks every Monday morning because they need to know if something broke. Or the one metric that goes straight into someone's bonus calculation. Or the report that answers "should we do this thing or not" with a number everyone agrees to trust.

The rest is furniture.

Anyone else have a beautifully designed dashboard just sitting there, looking expensive and ignored?

#DataAnalytics #BusinessIntelligence #DataDrivenDecisions #AnalyticsEngineering #DataScience

---

## April 09, 2026
**Topic:** The data quality problem nobody wants to own
**Tone:** Something I learned / observed / did at work | **Length:** Long

I'm working on a fraud detection pipeline this week. We're pulling transaction data from APIs, transforming it, running checks, loading it into Redshift. The schema looks clean. The tests pass. The dashboard updates every hour.

And then someone in fraud ops sends me a message.

"Why are 300 transactions showing null for merchant_category?"

I check the data. The field is there. It's just empty for about 10% of records. Not because the pipeline broke. Because upstream, the source system sometimes doesn't send it. And nobody caught it until someone tried to segment transactions by category.

So I ping engineering. They say the API is working as designed. If the merchant doesn't have a category on file, it returns null. That's expected behavior.

I ping the product team. They say analytics should handle nulls in reporting. That's just data hygiene.

I ping fraud ops. They say they need the category to route high-risk transactions. If it's missing, the rule doesn't fire.

Everyone is right. And the data is still wrong.

Nobody owns the gap between "the system works" and "the data is usable." Engineering owns the pipeline. Analytics owns the dashboard. The business owns the decision. But the space in between, where a null becomes a problem, that's nobody's job.

What actually fixes it is boring. You add a validation step that flags nulls before they hit the warehouse. You set up a Slack alert when the null rate crosses 5%. You add a fallback in the SQL that maps nulls to "Unknown" so the dashboard doesn't break. You document what the field actually means and when it's expected to be missing.

And then you put one person's name next to it. Not as blame. As ownership.

Because if everyone is responsible, nobody checks. And the business keeps seeing bad numbers until someone gets annoyed enough to ask why.

#DataQuality #DataEngineering #Analytics #DataPipelines #AnalyticsEngineering

---

## April 08, 2026
**Topic:** The metric that actually tells you if your data team is working
**Tone:** Credible Insight / Domain Authority | **Length:** Short

The best sign your data team is working: how many times people ask you to fix the *same* metric instead of building a new one.

If stakeholders keep coming back to argue about definitions, your team is shipping dashboards, not decisions.

When the same people stop asking "can you add this field" and start saying "according to the dashboard", you know the work landed.

Not glamorous. But it's the difference between being a ticket queue and being infrastructure.

#DataAnalytics #DataEngineering #AnalyticsEngineering #DataTeams #BusinessIntelligence

---

## April 07, 2026
**Topic:** Kafka is overkill for most companies
**Tone:** Relatable | **Length:** Medium

Most companies don't need Kafka.

I know that sounds boring. Real-time pipelines are fun to build. Streaming architecture looks great on a resume. But needing sub-second latency is rarer than LinkedIn makes it seem.

If your business can wait 15 minutes for the data, you don't need Kafka. If decisions happen once a day, you don't need Kafka. If the person reading the dashboard refreshes it twice a week, you really don't need Kafka.

A cron job running a Python script at 3am will handle most of what people are streaming. It's less impressive. It's also way easier to debug when it breaks.

Kafka makes sense when you actually can't wait. Fraud detection, live bidding, stock trades. Real consequences for delays measured in seconds. Outside of that, you're trading simplicity for a feature no one asked for.

Before you spin up a streaming platform, ask if anyone would notice if the data showed up 10 minutes later. If the answer is no, save yourself the trouble.

#DataEngineering #Analytics #Kafka #DataPipelines #RealTimeData

---

## April 06, 2026
**Topic:** Stop building data models nobody asked for
**Tone:** Funny / Witty | **Length:** Long

You spend three weeks building the most beautiful data model you've ever made.

Star schema. Perfect naming conventions. Slowly changing dimensions that actually work. Incremental loads. Tests on every join. Documentation that uses real sentences instead of table names as explanations.

You ship it. You send the email. You wait for someone to use it.

Two months later a stakeholder messages you asking for "quick data pull". They want to know the thing your model literally calculates. You send them the dashboard link. They say thanks but could you just send it in Excel. They never open the dashboard.

Or worse. They do open it. Once. Then they email you asking if you can add a filter. Then another filter. Then they ask if the data can update hourly instead of daily. Then they stop using it entirely and build their own pivot table from a CSV export they found on Sharepoint.

And you realize the model you were so proud of is now just sitting there. Humming along. Refreshing every night. Calculating metrics no one looks at. Using cloud compute that costs actual money.

The problem is not that the model is bad. The problem is that you built the model you wanted to build, not the model anyone actually needed.

I have done this. Multiple times. I got excited about the technical problem and forgot to ask the boring questions. Like who is actually going to use this. And for what. And how often. And could they just do it themselves in SQL if we gave them a clean base table instead.

Analytics engineers love building things that are elegant and scalable and reusable. Business stakeholders love getting an answer to the question they asked yesterday. Sometimes those overlap. A lot of times they do not.

The disconnect usually comes from this: we think in systems, they think in questions. We want to build once and serve many use cases. They want an answer to one question right now and maybe a different question next week.

Not saying we should stop building good models. Just saying maybe we should confirm someone will actually open the thing before we spend two weeks on dimension history tracking.

Anyone else have a model that is technically perfect and completely ignored.

#DataAnalytics #AnalyticsEngineering #DataModeling #BusinessIntelligence #DataStrategy

---

## April 03, 2026
**Topic:** The honest take on Azure vs AWS vs GCP for data
**Tone:** Relatable | **Length:** Long

I've used all three clouds for data work. Not in a sandbox. In production, with real pipelines, real budgets, real downstream teams who will let you know when something breaks.

Here's what actually matters.

AWS has the most mature data ecosystem. It just does. Redshift, Glue, S3, Athena, the whole stack has been around long enough that most edge cases are documented somewhere. The tooling feels stable. When something goes wrong, someone on Stack Overflow hit it three years ago. The downside is the pricing model. You will get surprised. Data transfer costs between services, Glue job runs that balloon, Redshift scaling that eats budget faster than you expect. You spend more time than you'd like in the billing console trying to figure out what happened.

GCP feels the cleanest to work in. BigQuery is genuinely fast and the SQL dialect is reasonable. The integration between services is smoother than AWS. You're not stitching together ten different things that were built in different decades. The problem is maturity. You will hit something that just doesn't work the way you expect, or that requires a workaround that feels hacky. The documentation is fine until it isn't. Pricing is more predictable than AWS, but you still need to watch it.

Azure is the one I've spent the most time in lately. Synapse, Data Factory, the whole suite. It works. It's not exciting. The tooling feels a bit clunky compared to GCP, the learning curve is steeper than AWS, but if you're in an enterprise environment it's probably already the standard. The integration with the rest of the Microsoft ecosystem is the real reason companies pick it. If your org runs on Microsoft everything, Azure makes sense. If you're starting from scratch, I'm not sure it's the first choice.

None of them are bad. But the choice matters less than people think. You adapt.

#DataEngineering #CloudComputing #Azure #AWS #DataAnalytics

---

## April 02, 2026
**Topic:** When ML makes things worse
**Tone:** Funny / Witty | **Length:** Short

We had a VP last year who wanted a machine learning model to predict which clients would churn.

Turned out 90% of churn happened when invoices were 60+ days overdue.

We built the model anyway. Took three weeks. Used gradient boosting, feature engineering, the works. Accuracy was great.

Then someone asked what we should do about it.

The answer was still: follow up on overdue invoices.

We could've written that query in ten minutes.

Has anyone else shipped a model that just automated common sense?

#DataScience #MachineLearning #Analytics #DataEngineering #ProductAnalytics

---

## April 02, 2026
**Topic:** When ML makes things worse
**Tone:** Funny / Witty | **Length:** Short

We spent three weeks tuning a churn prediction model. Precision, recall, feature engineering, the works.

Deployed it. Product team ignored it. Too opaque. Instead they used "customer hasn't logged in for 60 days" as their trigger.

Guess what performed better in the A/B test.

The rule. By a lot.

Sometimes the fancy model just gives you a worse version of common sense that nobody trusts and breaks every time the data shifts.

Anyone else build something technically cool that lost to an IF statement?

#DataScience #MachineLearning #Analytics #DataEngineering #ProductAnalytics

---

