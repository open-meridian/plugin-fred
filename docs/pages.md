# Pages

Both pages are the data role's, the same on every data plugin, under
**Manage**, for the plugin's admins. Neither shows a rate. Each is also a
read tool on the deployment's MCP, answering what the page shows, under the
same names on every data plugin.

## Connection (`read_connection`)

How the plugin reaches FRED, and how the last check went:

- the head's status: answering, checking, no key, nothing kept current, not
  answering, or records not held;
- **Key:** the mode (Live, Sample data or No key), whether the FRED API key
  is set (never its value), and what FRED serves;
- **Limits and use:** FRED's limit (120 requests a minute for a key) and the
  pace the plugin keeps, the requests made, the last call and error;
- **Stream:** it does not stream;
- **Sources:** one line per publisher's rates FRED carries (the New York
  Fed's reference rates, the FOMC target range, €STR, Treasury's par
  curves): its state, the latest day read, and the calls made. A row's `…`
  opens its publisher, how many series, the last error and how many answers
  are kept.

## Datasets (`read_datasets`)

What the plugin serves:

- **Served:** its three datasets as the deployment's catalogue lists them,
  with the terms each declares, whether a deployment admin has licensed it,
  what it recorded and declined, and its **Lag**: how long after the start
  of a rate's day FRED had it, the median;
- **Wants:** the standing wants it keeps current, and the last wants it
  answered; **Subjects**;
- **Records:** each reference rate or curve it records against, the series
  recorded against it, and the deployment's record or why there is none;
- **FRED series:** each series it carries, searchable: what it is a rate
  of, its copyright class and dataset, a mark where its class changed,
  whether it is kept current. A row's `…` opens FRED's title, the class
  changes, its first observation and FRED's last update. FRED's notice and
  the citation it asks for are below.
