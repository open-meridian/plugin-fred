# Overview

FRED, the Federal Reserve Bank of St. Louis's economic data service, carries
hundreds of thousands of series from many publishers. This plugin reads the
interest-rate series among them through FRED's API and puts them into your
deployment's lake as rates, where a reporting or pricing plugin reads them.

It is a data plugin: its first-use path, its two pages and its Summary figures are every data plugin's, described once on [Using a data plugin](https://open-meridian.dev/how-to/using-a-data-plugin/). These sections cover what is FRED's own.

## What it carries

This version carries rate series only, each recorded against a reference rate
or curve the platform keeps:

| Record | FRED series |
|---|---|
| SOFR, EFFR and OBFR (New York Fed) | `SOFR`, `EFFR`, `OBFR`, each a daily fixing with its 1st, 25th, 75th and 99th percentiles and its volume |
| The 30, 90 and 180-day SOFR averages | `SOFR30DAYAVG`, `SOFR90DAYAVG`, `SOFR180DAYAVG` |
| The SOFR Index | `SOFRINDEX`, an index level, 2 April 2018 = 1 |
| The FOMC target range, lower and upper bound | `DFEDTARL`, `DFEDTARU` |
| €STR (ECB) | `ECBESTRVOLWGTTRMDMNRT`, with its volume |
| Treasury's par yield curve | `DGS1MO` to `DGS30`: eleven points, 1 month to 30 years |
| Treasury's par real yield curve | `DFII5` to `DFII30`: five points, 5 to 30 years |

A curve is one record, and each point a rate with its tenor: FRED's `DGS10`
is the 10-year point of Treasury's par curve, the same subject and tenor as
Treasury's own figure.

Macro series (GDP, inflation, employment) come in a later version.

## FRED beside each publisher's own plugin

Every series here is first published by someone else: the New York Fed, the
Federal Reserve Board, the ECB or the Treasury. Each has its own plugin, and
that plugin is the primary source. FRED's dataset is a second source of the
same rates, with longer history in places (the 10-year Treasury yield from
1962). Your deployment's source priority says which one a reader gets by
default.

## When rates arrive

The plugin checks each series it keeps current every hour, and records what
FRED changed since. A rate belongs to its day, New York time. FRED states
when it last changed a series, not when each value appeared, so only the
latest value read when it is new carries a published time.

A value FRED revises (a fixing its publisher corrects the same day) becomes
the next version of the same rate. A day FRED shows no value for, a holiday
or a tenor not published, is no rate: never a zero.

## Copyright classes

FRED tags each series with its copyright: public domain, copyrighted with
citation required, or copyrighted with pre-approval required. The plugin
serves each class as its own dataset, so your licence for each is one
decision. A series whose class changes moves dataset, and the Datasets page
shows when.

## What it does not do

- It shows no rate on its own pages: rates are read by other plugins.
- It never creates a record. A rate whose record your deployment does not
  hold waits, and is reported missing.
- It never stores or shows your API key.
