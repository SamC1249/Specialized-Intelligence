# Wikimedia Commons: `categorymembers` generator note

## Endpoint

```
https://commons.wikimedia.org/w/api.php
  ?action=query
  &generator=categorymembers
  &gcmtitle=Category:Videos_of_cooking
  &gcmtype=file
  &gcmlimit=100
  &prop=imageinfo
  &iiprop=url|size|mime|extmetadata
  &format=json
```

## Why we care

Free-text `gsrsearch` misses files whose title/description don't contain
the query term but which humans have explicitly categorized. For
`Category:Videos_of_cooking` there are 75 files (2026-07 census), plus
4 subcategories (`Videos of cooking recipes`, `Videos of dish washing`,
`Videos of cooking from India`, `Videos of kitchens`). Free-text
`cooking` currently returns ≤50 hits for the same query terms.

## Response shape

Categorymembers-generated queries return the *same* `query.pages[…]`
dict structure as search-generated ones — critically, our existing
`WikimediaCommonsSource.parse()` already handles it. All that's needed
is a second `search()` path.

## What we shipped

`WikimediaCommonsSource(category="Videos of cooking")` — an optional
constructor kwarg that switches `search()` from `gsrsearch` to
`generator=categorymembers`. The `parse()` code path is unchanged; a
new fixture `tests/fixtures/wikimedia/category_cooking.json` exercises
it.

## Pagination

Commons paginates `categorymembers` via `continue.cmcontinue`. For seed
crawls we accept a single page — page size 50 is more than our current
`max_results` cap. Pagination is a follow-up when we scale up.
