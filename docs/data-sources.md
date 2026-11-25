# Data sources

## Where the postings come from

Greenhouse, Lever, Workable and Ashby each publish a JSON job board for every
company that uses them. No auth, no scraping HTML, stable ids, real posting
dates. That is the whole list for now. Thirty to fifty companies should be
enough to get past a thousand postings.

## What is not used

JobStreet, Glints, Kalibrr, LinkedIn. Their terms do not allow automated
collection, and a robots.txt file is not permission. It seemed wrong to start a
project about the job market by ignoring how that market's data is licensed.

There is also a manual CSV import for postings I read myself, but that is a
supplement. It would not get near a thousand rows on its own.

## What gets stored

Title, company, city, seniority, work mode, a cleaned description for
processing, the source URL, and when it was fetched.

Dropped before insert: emails, phone numbers, recruiter names, anything that
looks like contact details. Raw payloads are pruned after 90 days. Descriptions
never leave the database through the API or the dashboard.

## What this sample is not

- a census. Only companies that use a modern ATS.
- evenly spread across cities.
- real time.

If I ever add a monthly trend it would only show postings still open on the day
I fetched them. Older postings are less likely to still be listed, so recent
months always look busier. Probably not worth showing.
