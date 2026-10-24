# Terms

## Who checks this plugin

Whoever installs it carries its risk. Wherever it is listed, the listing is
not an endorsement; the registry it came from says what, if anything, it
checked. The
[Platform Terms](https://open-meridian.com/terms) govern.

## FRED's terms

What this plugin's builders noted, to check against FRED's own words, which
can change. Not legal advice.

- FRED's API needs a free key, and its
  [API terms of use](https://fred.stlouisfed.org/docs/api/terms_of_use.html)
  apply to its use: among them, a notice that the product uses the FRED® API
  but is not endorsed or certified by the Federal Reserve Bank of St. Louis,
  and no use that replicates FRED's service.
- **Copyright is per series** ([FRED's legal notices](https://fred.stlouisfed.org/legal/)):
  each series is tagged public domain (citation requested), copyrighted with
  citation required, or copyrighted with pre-approval required. Copyrighted
  series belong to their publishers, and the API terms add that using a
  series whose notes say "Copyright" for anything beyond personal use needs
  its owner's permission, which FRED cannot grant. Check each `fred_cited`
  series' own publisher's terms (the New York Fed's for SOFR, EFFR and OBFR)
  before licensing the dataset beyond personal use.
- ICE BofA series (index yields and spreads) keep only three years on FRED,
  and reproducing them needs ICE's permission. This version carries none.
- Each series' own publisher may state terms of its own: the New York Fed's
  reference rates carry its notice and disclaimer, and SOFR and BGCR rest on
  data it licenses.

## Attribution

Show FRED's notice, and cite each series as FRED's suggested citation gives
it: the publisher, the series' title and ID, "retrieved from FRED, Federal
Reserve Bank of St. Louis". The Datasets page shows the notice. Each dataset's
default licence declares its class's terms; the attribution belongs in your
licence's note until the licence carries it.

The datasets' licences on your Data sources page are what your deployment
records; neither the plugin nor this page says whether your use meets
anyone's terms. This project is not affiliated with or endorsed by the
Federal Reserve Bank of St. Louis or any series' publisher.

## The licence

The plugin is Apache-2.0. The responses committed with it are FRED's values,
titles, update times and copyright tags as published on 23 October 2026,
laid out as FRED's API answers them.
