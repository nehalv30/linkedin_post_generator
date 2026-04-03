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

