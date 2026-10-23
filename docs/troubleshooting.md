# Troubleshooting

## Connection

| What you see | What it means | What to do |
|---|---|---|
| **No key** | No FRED API key is set: nothing is asked of FRED | Enter your key in Settings |
| **Not answering** | No check has reached FRED, or FRED refused the key | Check the key, and the deployment's outbound access to api.stlouisfed.org; the detail says what FRED answered |
| **Answering**, with a warning | Some series were read; one was not | Nothing, usually: the next check runs within the hour. The detail names the series |
| **Nothing kept current** | No series is listed in Settings, and no reader has a standing want | Nothing, if that is what you want: series are fetched when wanted. Otherwise list them in Settings |
| Calls rate-limited | FRED answered 429: more than 120 requests a minute for the key | The plugin waits until the next check; check nothing else uses the same key heavily |

## Rates and records

| What you see | What it means | What to do |
|---|---|---|
| **N records not held** | A reference rate or curve the platform seeds is not in your deployment | Ask for it at the Instruments page; its rates are recorded at the next check after |
| A series' class **changed** | FRED changed its copyright tag | Check that dataset's licence; the series is now served under its new class's dataset |
| A value the plugin could not read | FRED stated something that is not a number | It is not recorded; the Datasets page lists it |

## Wants and licences

| What you see | What it means | What to do |
|---|---|---|
| A day declined, *source silent* | FRED has no value that day: a holiday, or not published yet | Wait for the publisher's next release |
| A subject declined, *not covered* | No series this version carries is about that record under that dataset's class | Ask the dataset of the series' class, or the publisher's own plugin |
| A day declined, *beyond history* | Before the series' first observation | Ask the publisher's own plugin, or a later day |
| A subject declined, *not entitled* | No FRED API key is set | Enter your key in Settings |
| Datasets: **Not licensed yet** | No deployment admin has licensed the dataset | Ask a deployment admin to license it on Data sources |
