# Crypto Gambling Site Analyzer

Automated pipeline that classifies crypto gambling platforms by AML compliance and fraud risk using web scraping and regex-based extraction.

Built as a test assignment for a crypto analyst role — demonstrates programmatic site scraping with graceful fallbacks, structured data extraction from legal text, and batch Excel output.

---

## What it does

For each URL in the input spreadsheet, the pipeline runs four steps:

1. **Scrape** — fetches the homepage and legal pages (`/terms`, `/about`, `/legal`, `/privacy`). If the site returns an error or is blocked (403/429/Cloudflare), falls back to the nearest [web.archive.org](https://web.archive.org) snapshot automatically.

2. **Extract** — regex extractors pull 15+ structured fields from the raw page text: KYC/AML policies, license details, legal entity name, country of registration, supported cryptocurrencies, blockchain networks, payout speed, and more.

3. **Supplement** — pulls additional data from AskGamblers: player ratings, complaint counts, verified payout speed, year founded.

4. **Technical checks** — SSL certificate validity and domain age via WHOIS.

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
| N | legal_entity_name | Regex — operating company name |
| O | company_reg_number | Regex |
| P | company_reg_country | Regex — country of registration |
| Q | license | Regex — licensing authority and number |
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

---

## Setup

**Requirements:** Python 3.11+

```bash
git clone https://github.com/LiD022/cryptosite_analyzer.git
cd cryptosite_analyzer
pip install -r requirements.txt
```

---

## Usage

```bash
# Full run — all sites
python analyzer.py

# First 10 sites only (good for testing)
python analyzer.py --limit 10

# Start from row 20 (useful for resuming an interrupted run)
python analyzer.py --start 20
```

Results are saved to `results/output.xlsx`.

---

## How it works

### Scraping strategy

Many crypto gambling sites use Cloudflare or other anti-bot protection. The scraper handles this in layers:

1. Try the live site with realistic browser headers
2. On 403/429/timeout — query web.archive.org for the most recent snapshot
3. Fetch the archived homepage and attempt `/terms` from the archive as well

This gives useful text even for sites that block automated requests or have gone offline.

### Extraction

Each field is extracted by a dedicated set of regex patterns tuned to gambling site legal text. Fields like `legal_entity_name`, `license`, and `company_reg_country` use patterns that distinguish actual registration data from generic country mentions.

### Pipeline flow

```
Input Excel (URLs)
      │
      ▼
  scraper.py        live fetch → archive.org fallback on block/timeout
      │
      ▼
 extractors.py      regex: KYC, AML, license, legal entity, currencies, etc.
      │
      ▼
  analyzer.py       AskGamblers data + SSL + WHOIS → write to Excel
```

---

## Project structure

```
├── analyzer.py                          Main pipeline orchestrator
├── scraper.py                           Web scraping with archive.org fallback
├── extractors.py                        15+ regex-based attribute extractors
├── requirements.txt
├── tests/
│   └── test_extractors.py               Unit tests for regex extractors (15 tests)
└── Gembling_zadanie_Istomin_N.xlsx      Input dataset
```

---

## Running tests

```bash
pytest tests/ -v
```
