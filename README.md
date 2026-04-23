# Crypto Gambling Site Analyzer

Automated pipeline that classifies crypto gambling platforms by AML compliance and fraud risk.

Built as a test assignment for a crypto analyst role — demonstrates programmatic site scraping, regex-based data extraction from legal text, and a hybrid AI enrichment pipeline using Claude.

---

## What it does

For each URL in the input spreadsheet, the pipeline runs four steps:

1. **Scrape** — fetches the homepage and legal pages (`/terms`, `/about`, `/legal`, `/privacy`). If the site is unreachable, falls back to the nearest [web.archive.org](https://web.archive.org) snapshot automatically.

2. **Extract** — regex extractors pull 15+ structured fields from the raw page text: KYC/AML policies, license details, legal entity name, country of registration, supported cryptocurrencies, blockchain networks, payout speed, and more.

3. **Enrich with AI** — a single [Claude Haiku](https://www.anthropic.com/claude) API call per site receives the regex output as context, fills in any fields the regex couldn't determine, and produces:
   - `aml_risk_score` — integer 1–10 (10 = highest risk)
   - `aml_risk_reasoning` — 2–3 sentence explanation of the score
   - `fraud_flags` — list of specific red flags found on the site

4. **Supplement** — pulls additional data from AskGamblers: player ratings, complaint counts, verified payout speed.

Results are written row-by-row into `results/output.xlsx`, preserving the original spreadsheet formatting.

---

## Output fields

| Column | Field | Source |
|--------|-------|--------|
| B | platform_name | URL parsing |
| C | status_code | Scraper — `active` / `inactive` / `unreachable` |
| D | platform_type | Regex — online casino / betting / lottery / slots |
| E | is_AML | Regex — AML policy mentioned? (`y`/`n`) |
| F | is_KYC | Regex — KYC required? (`y`/`n`) |
| G | KYC_type | Regex — `KYC` / `OPTIONAL_KYC` / `NO_KYC` |
| I | web_archive_url | Archive.org fallback URL |
| N | legal_entity_name | Regex → AI fallback |
| O | company_reg_number | Regex |
| P | company_reg_country | Regex → AI fallback |
| Q | license | Regex → AI fallback |
| R | safety_score | AskGamblers |
| S | player_rating | AskGamblers |
| T | complaints_total | AskGamblers |
| U | complaints_resolved | AskGamblers |
| V | payout_speed | Regex / AskGamblers |
| W | games_count | Regex / AskGamblers |
| X | supported_crypto | Regex — `BTC, ETH, USDT, …` |
| Y | supported_fiat | Regex — `USD, EUR, …` |
| Z | crypto_only | Regex — `y` if no fiat accepted |
| AA | blockchains | Regex — `Ethereum, TRON, BNB Chain, …` |
| AB | is_decentralized | Regex — DeFi/on-chain platform? (`y`/`n`) |
| AC | ssl_valid | SSL certificate check — `valid` / `invalid` / `expired` |
| AD | domain_age_years | WHOIS lookup |
| AE | founded_year | AskGamblers |
| **AF** | **aml_risk_score** | **AI — 1 (low risk) to 10 (high risk)** |
| **AG** | **aml_risk_reasoning** | **AI — explanation of the score** |
| **AH** | **fraud_flags** | **AI — list of red flags found** |

---

## Setup

**Requirements:** Python 3.11+

```bash
git clone https://github.com/LiD022/cryptosite_analyzer.git
cd cryptosite_analyzer
pip install -r requirements.txt
```

Set your Anthropic API key (required for AI enrichment):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

```bash
# Full run — all sites with AI enrichment
python analyzer.py

# First 10 sites only (good for testing)
python analyzer.py --limit 10

# Start from row 20 (useful for resuming an interrupted run)
python analyzer.py --start 20

# Fast mode — skip LLM, no API key needed
python analyzer.py --no-llm
```

Results are saved to `results/output.xlsx`.

---

## Methodology

### Why hybrid regex + LLM?

Regex is fast, deterministic, and costs nothing. It reliably handles the majority of sites where legal text follows predictable patterns. The LLM (Claude Haiku) is called **once per site** as a single enrichment pass:

- **Gap-filling:** the model receives already-extracted fields as context so it only works on what regex couldn't determine — no redundant work, minimal token usage
- **Risk scoring:** produces a holistic AML/fraud assessment based on the full context of the site

**Cost:** ~$0.001 per site. **Latency:** ~2 seconds per site added.

### How the AML risk score works

The model evaluates a combination of signals:

| Signal | Low risk | High risk |
|--------|----------|-----------|
| License | MGA, UKGC, Isle of Man | Curaçao, none |
| KYC | Mandatory full verification | Optional or absent |
| Anonymity | Not promoted | Explicitly advertised |
| Currencies | Fiat + crypto | Crypto-only |
| Architecture | Centralized, regulated | DeFi, non-custodial |
| Domain age | Established (5+ years) | New or no WHOIS data |

### Pipeline flow

```
Input Excel (URLs)
      │
      ▼
  scraper.py          fetch homepage + /terms pages + archive.org fallback
      │
      ▼
 extractors.py        regex: KYC, AML, license, legal entity, currencies, etc.
      │
      ▼
 llm_enricher.py      Claude Haiku: fill gaps + aml_risk_score + fraud_flags
      │
      ▼
  analyzer.py         AskGamblers data + SSL + WHOIS → write to Excel
```

---

## Project structure

```
├── analyzer.py                          Main pipeline orchestrator
├── scraper.py                           Web scraping with archive.org fallback
├── extractors.py                        15+ regex-based attribute extractors
├── llm_enricher.py                      Claude API: gap-fill + AML risk scoring
├── requirements.txt
├── tests/
│   ├── test_extractors.py               Unit tests for regex extractors (15 tests)
│   └── test_llm_enricher.py             Mock-based tests for LLM enricher (3 tests)
└── Gembling_zadanie_Istomin_N.xlsx      Input dataset
```

---

## Running tests

```bash
pytest tests/ -v
```
