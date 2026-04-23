# Crypto Gambling Site Analyzer — Design Spec
**Date:** 2026-04-23  
**Author:** Nikita Istomin  
**Status:** Approved

---

## Problem

Manually classifying 100+ crypto gambling sites for AML/fraud risk is time-consuming and error-prone. Sites use inconsistent terminology, many are partially offline, and raw regulatory data is buried in legal text.

## Goal

Build an automated pipeline that:
1. Scrapes each site (with archive.org fallback)
2. Extracts structured attributes via regex (fast, deterministic)
3. Uses an LLM to fill gaps and produce an AML risk score with reasoning (one API call per site)
4. Writes all results to Excel

---

## Architecture

```
Input Excel (URLs)
      │
      ▼
  scraper.py          — fetches homepage + /terms pages, archive fallback
      │
      ▼
 extractors.py        — regex extraction: KYC, AML, license, legal entity,
                        country, currencies, blockchains, payout speed, games
      │
      ▼
 llm_enricher.py      — single Claude API call per site:
                        1. fills empty fields regex missed
                        2. outputs aml_risk_score (1-10) + reasoning + fraud_flags
      │
      ▼
  analyzer.py         — orchestrates the pipeline, writes to output.xlsx
```

---

## Components

### `scraper.py` (unchanged)
- Fetches homepage + /about, /terms, /legal, /privacy, /faq
- Falls back to web.archive.org if site unreachable
- Returns `{url, status, archive_url, text, pages_fetched}`

### `extractors.py` (unchanged)
- Pure regex extraction, no external calls
- Returns ~15 structured fields

### `llm_enricher.py` (new)
Input: `extracted: dict`, `site_text: str`

Single Claude API call with structured prompt:
- Context: what regex already found (so LLM doesn't repeat work)
- Task A: fill only the fields that are `None` / "other" / unclear
- Task B: produce `aml_risk_score` (1=low risk, 10=high risk), `aml_risk_reasoning` (2-3 sentences), `fraud_flags` (list of specific red flags found)

Output: merged dict with enriched fields + risk assessment

Model: `claude-haiku-4-5-20251001` (fast + cheap for batch processing)

### `analyzer.py` (updated)
- Adds `--no-llm` flag to skip enrichment (for fast local runs)
- Adds `--limit` and `--start` (already exist)
- Reads `ANTHROPIC_API_KEY` from env

---

## Output Columns (Excel)

| Column | Field | Source |
|--------|-------|--------|
| B | platform_name | parsed from URL |
| C | status_code | scraper |
| D | platform_type | regex |
| E | is_AML | regex |
| F | is_KYC | regex |
| G | KYC_type | regex |
| I | web_archive_url | scraper |
| N | legal_entity_name | regex → LLM fallback |
| O | company_reg_number | regex |
| P | company_reg_country | regex → LLM fallback |
| Q | license | regex → LLM fallback |
| R | safety_score | AskGamblers |
| S | player_rating | AskGamblers |
| T | complaints_total | AskGamblers |
| U | complaints_resolved | AskGamblers |
| V | payout_speed | regex / AskGamblers |
| W | games_count | regex / AskGamblers |
| X | supported_crypto | regex |
| Y | supported_fiat | regex |
| Z | crypto_only | regex |
| AA | blockchains | regex |
| AB | is_decentralized | regex |
| AC | ssl_valid | SSL check |
| AD | domain_age_years | WHOIS |
| AE | founded_year | AskGamblers |
| AF | aml_risk_score | LLM (1-10) |
| AG | aml_risk_reasoning | LLM |
| AH | fraud_flags | LLM |

---

## Repo Structure

```
crypto-analyze/
├── analyzer.py          # main pipeline orchestrator
├── scraper.py           # web scraping + archive fallback
├── extractors.py        # regex-based attribute extraction
├── llm_enricher.py      # Claude API: gap-fill + AML risk scoring
├── requirements.txt     # httpx, beautifulsoup4, openpyxl, python-whois, anthropic
├── .gitignore
├── README.md            # setup, usage, methodology, example output
├── Gembling_zadanie_Istomin_N.xlsx  # input data
└── results/             # gitignored
```

---

## Key Decisions

- **One LLM call per site**: pass regex results as context so LLM only fills gaps — efficient, ~$0.001/site with Haiku
- **Haiku model**: fastest + cheapest for batch; accuracy is sufficient for structured extraction + risk scoring
- **`--no-llm` flag**: allows running without API key for quick local testing
- **Deterministic first**: regex runs unconditionally; LLM is additive — results are reproducible even without API key
