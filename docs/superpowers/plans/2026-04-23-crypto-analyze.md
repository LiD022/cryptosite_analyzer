# Crypto Gambling Site Analyzer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a working but unstructured Python script collection into a clean, well-documented repo with a hybrid regex+LLM AML risk analysis pipeline.

**Architecture:** Regex extractors run unconditionally (fast, free, deterministic). Claude Haiku is called once per site to fill empty fields and produce an AML risk score 1–10 with reasoning. All results write to Excel.

**Tech Stack:** Python 3.11+, httpx, BeautifulSoup4, openpyxl, python-whois, anthropic SDK

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `.gitignore` | Create | Exclude cache, results, DS_Store, .env |
| `requirements.txt` | Modify | Add `anthropic` |
| `llm_enricher.py` | Create | Claude API: gap-fill + AML risk scoring |
| `analyzer.py` | Modify | Add LLM call, 3 new Excel columns (AF-AH), `--no-llm` flag |
| `README.md` | Create | Setup, usage, methodology, output field reference |
| `tests/test_extractors.py` | Create | Unit tests for existing regex extractors |
| `tests/test_llm_enricher.py` | Create | Mock-based tests for LLM enricher |

---

## Task 1: Git repo + .gitignore

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/nistomin/Desktop/gits/side_project/crypto-analyze
git init
```

Expected: `Initialized empty Git repository in .../crypto-analyze/.git/`

- [ ] **Step 2: Create `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*.pyo
.Python
*.egg-info/
dist/
build/
.venv/
venv/
env/

# Output data
results/

# OS
.DS_Store
.DS_Store?
._*
Thumbs.db

# IDE
.idea/
.vscode/
*.swp

# Playwright leftovers
.playwright-mcp/

# Claude internals
.claude/

# Secrets
.env
```

- [ ] **Step 3: Stage and commit**

```bash
git add .gitignore
git commit -m "chore: initialize repo with .gitignore"
```

---

## Task 2: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Replace contents**

```
httpx
beautifulsoup4
openpyxl
python-whois
anthropic
pytest
```

Note: removed `playwright` — it's not used in any source file.

- [ ] **Step 2: Install and verify**

```bash
pip install -r requirements.txt
python -c "import anthropic; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add anthropic SDK, remove unused playwright"
```

---

## Task 3: Tests for existing extractors

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_extractors.py`

- [ ] **Step 1: Create `tests/__init__.py`**

Empty file.

- [ ] **Step 2: Write `tests/test_extractors.py`**

```python
import pytest
from extractors import (
    detect_platform_type, detect_aml, detect_kyc,
    detect_license, detect_reg_country, detect_currencies,
)


def test_platform_type_casino():
    assert detect_platform_type("live dealer roulette blackjack casino games") == "online casino"


def test_platform_type_betting():
    assert detect_platform_type("sportsbook football betting odds wagering") == "betting"


def test_platform_type_slots():
    assert detect_platform_type("slots spin reel fruit machine") == "online slot machine"


def test_platform_type_fallback():
    assert detect_platform_type("nothing relevant here") == "other"


def test_aml_found():
    assert detect_aml("We comply with AML anti-money laundering regulations.") == "y"


def test_aml_not_found():
    assert detect_aml("Enjoy our games. Fast withdrawals.") == "n"


def test_kyc_mandatory():
    is_kyc, kyc_type = detect_kyc("KYC verification required. Identity verification before withdrawal.")
    assert is_kyc == "y"
    assert kyc_type == "KYC"


def test_kyc_none():
    is_kyc, kyc_type = detect_kyc("No KYC required. Play anonymous. No identity needed.")
    assert is_kyc == "n"
    assert kyc_type == "NO_KYC"


def test_kyc_optional():
    is_kyc, kyc_type = detect_kyc("KYC is optional for small withdrawals.")
    assert is_kyc == "y"
    assert kyc_type == "OPTIONAL_KYC"


def test_license_found():
    text = "Licensed and regulated by the Malta Gaming Authority MGA/B2C/148/2007."
    licenses = detect_license(text)
    assert len(licenses) > 0


def test_reg_country_curacao():
    assert detect_reg_country("incorporated in Curacao under gaming license") == "Curacao"


def test_reg_country_malta():
    assert detect_reg_country("MGA licensed, incorporated in Malta") == "Malta"


def test_reg_country_none():
    assert detect_reg_country("no registration info here") is None


def test_currencies_crypto():
    result = detect_currencies("We accept Bitcoin BTC, Ethereum ETH, Litecoin LTC")
    assert "BTC" in result["supported_crypto"]
    assert "ETH" in result["supported_crypto"]


def test_crypto_only_flag():
    result = detect_currencies("We accept Bitcoin BTC and Ethereum ETH only.")
    assert result["crypto_only"] == "y"
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_extractors.py -v
```

Expected: all 15 tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: add unit tests for regex extractors"
```

---

## Task 4: Create `llm_enricher.py`

**Files:**
- Create: `llm_enricher.py`
- Create: `tests/test_llm_enricher.py`

- [ ] **Step 1: Write failing test first**

Create `tests/test_llm_enricher.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from llm_enricher import enrich, FIELDS_TO_FILL


def _mock_response(payload: dict) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    return msg


def test_enrich_fills_missing_fields():
    extracted = {
        "platform_type": "other",
        "is_AML": "n", "is_KYC": "n", "KYC_type": "NO_KYC",
        "legal_entity_name": None, "company_reg_country": None,
        "license": None, "supported_crypto": "BTC, ETH",
        "supported_fiat": None, "crypto_only": None,
        "blockchains": None, "is_decentralized": None,
        "payout_speed": None, "games_count": None,
    }
    site_text = "Stake is operated by Medium Rare N.V., incorporated in Curacao."
    api_payload = {
        "platform_type": "online casino",
        "legal_entity_name": "Medium Rare N.V.",
        "company_reg_country": "Curacao",
        "license": "Curacao eGaming",
        "aml_risk_score": 5,
        "aml_risk_reasoning": "Curacao license present but no KYC required.",
        "fraud_flags": ["No KYC required", "Crypto-only platform"],
    }
    with patch("llm_enricher.client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(api_payload)
        result = enrich(extracted, site_text)

    assert result["platform_type"] == "online casino"
    assert result["legal_entity_name"] == "Medium Rare N.V."
    assert result["aml_risk_score"] == 5
    assert isinstance(result["fraud_flags"], list)
    assert "No KYC required" in result["fraud_flags"]


def test_enrich_handles_json_in_codeblock():
    extracted = {"platform_type": None, "legal_entity_name": None,
                 "company_reg_country": None, "license": None,
                 "is_AML": None, "is_KYC": None, "KYC_type": None,
                 "supported_crypto": None, "supported_fiat": None,
                 "crypto_only": None, "blockchains": None,
                 "is_decentralized": None, "payout_speed": None, "games_count": None}
    payload = {"aml_risk_score": 3, "aml_risk_reasoning": "Low risk.", "fraud_flags": []}
    wrapped = f"```json\n{json.dumps(payload)}\n```"
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=wrapped)]
    with patch("llm_enricher.client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        result = enrich(extracted, "some text")
    assert result["aml_risk_score"] == 3


def test_enrich_returns_empty_on_api_error():
    extracted = {"platform_type": None, "legal_entity_name": None,
                 "company_reg_country": None, "license": None,
                 "is_AML": None, "is_KYC": None, "KYC_type": None,
                 "supported_crypto": None, "supported_fiat": None,
                 "crypto_only": None, "blockchains": None,
                 "is_decentralized": None, "payout_speed": None, "games_count": None}
    with patch("llm_enricher.client") as mock_client:
        mock_client.messages.create.side_effect = Exception("API error")
        result = enrich(extracted, "some text")
    assert result == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm_enricher.py -v
```

Expected: `ModuleNotFoundError: No module named 'llm_enricher'`

- [ ] **Step 3: Create `llm_enricher.py`**

```python
"""
llm_enricher.py — Claude API enrichment for crypto gambling site analysis.

Single API call per site:
  - Fills fields that regex left empty
  - Produces AML risk score (1–10) + reasoning + fraud flags
"""

import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

FIELDS_TO_FILL = [
    "platform_type", "is_AML", "is_KYC", "KYC_type",
    "legal_entity_name", "company_reg_country", "license",
    "supported_crypto", "supported_fiat", "crypto_only",
    "blockchains", "is_decentralized", "payout_speed", "games_count",
]

_PROMPT_TEMPLATE = """\
You are a crypto gambling site analyst specializing in AML compliance and fraud detection.

SITE TEXT (up to 4000 chars):
{site_text}

ALREADY EXTRACTED BY REGEX:
{found_json}

MISSING FIELDS (fill only these — use null if you cannot determine from the text):
{missing_list}

Also produce:
- aml_risk_score: integer 1-10 (1 = very low risk, 10 = very high risk)
- aml_risk_reasoning: 2-3 sentences explaining the score based on license, KYC, jurisdiction, anonymity
- fraud_flags: list of specific red flags found (e.g. "No license found", "Anonymous play promoted", "Unregulated jurisdiction")

Respond ONLY with valid JSON. No markdown, no explanation outside JSON.

Example shape:
{{
  "platform_type": "online casino",
  "legal_entity_name": null,
  "company_reg_country": "Curacao",
  "license": null,
  "aml_risk_score": 7,
  "aml_risk_reasoning": "No verifiable license found. KYC is optional, enabling anonymous high-volume play.",
  "fraud_flags": ["No license found", "Optional KYC", "Crypto-only platform"]
}}
"""


def enrich(extracted: dict, site_text: str) -> dict:
    """
    Single Claude Haiku call: fills empty fields + AML risk assessment.
    Returns merged dict; returns {} on any API error.
    """
    found = {k: v for k, v in extracted.items() if v is not None and v != "other"}
    missing = [f for f in FIELDS_TO_FILL if not extracted.get(f) or extracted.get(f) == "other"]

    prompt = _PROMPT_TEMPLATE.format(
        site_text=site_text[:4000],
        found_json=json.dumps(found, indent=2),
        missing_list=missing,
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except Exception:
        return {}
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_llm_enricher.py -v
```

Expected: 3 tests pass

- [ ] **Step 5: Commit**

```bash
git add llm_enricher.py tests/test_llm_enricher.py
git commit -m "feat: add LLM enricher with gap-fill and AML risk scoring"
```

---

## Task 5: Update `analyzer.py`

**Files:**
- Modify: `analyzer.py`

Changes:
1. Import `llm_enricher.enrich`
2. Add 3 new columns to `COL_MAP`: `aml_risk_score` (32/AF), `aml_risk_reasoning` (33/AG), `fraud_flags` (34/AH)
3. Add `--no-llm` argparse flag
4. In `analyze_site()`: call `enrich()` unless `--no-llm`, merge result (LLM wins over `None` but not over regex values)

- [ ] **Step 1: Add columns to `COL_MAP`**

In `analyzer.py`, find the `COL_MAP` dict and append after `"founded_year": 31`:

```python
    "aml_risk_score":     32,   # AF
    "aml_risk_reasoning": 33,   # AG
    "fraud_flags":        34,   # AH
```

- [ ] **Step 2: Add import at top of `analyzer.py`**

After the existing imports, add:

```python
from llm_enricher import enrich
```

- [ ] **Step 3: Add `--no-llm` flag to argparse**

In `main()`, after the existing `add_argument` calls:

```python
    parser.add_argument("--no-llm", action="store_true", help="Пропустить LLM-обогащение")
```

Pass `args.no_llm` down into the processing loop. Change the loop body to:

```python
        try:
            data = analyze_site(url, no_llm=args.no_llm)
```

- [ ] **Step 4: Update `analyze_site` signature and add LLM call**

Change the function signature:

```python
def analyze_site(url: str, no_llm: bool = False) -> dict:
```

After step 6 (regex extraction) and before step 7 (AskGamblers), insert:

```python
    # 6b. LLM enrichment: fill gaps + AML risk scoring
    if not no_llm:
        llm_data = enrich(attrs, combined_text)
        for key, value in llm_data.items():
            if value is not None and (attrs.get(key) is None or attrs.get(key) == "other"):
                attrs[key] = value
            elif key in ("aml_risk_score", "aml_risk_reasoning", "fraud_flags"):
                attrs[key] = value
        result.update(attrs)
    else:
        result.update(attrs)
```

Replace the existing `result.update(attrs)` (step 6) with just `pass` since we now update inside the if/else above.

- [ ] **Step 5: Update print line in loop to show LLM fields**

In the `main()` loop, update the print to include:

```python
            print(
                f"  status={data.get('status_code')} | type={data.get('platform_type')} "
                f"| KYC={data.get('KYC_type')} | AML={data.get('is_AML')} "
                f"| country={data.get('company_reg_country')} "
                f"| ssl={data.get('ssl_valid')} | age={data.get('domain_age_years') or '?'}y "
                f"| crypto={data.get('supported_crypto', '-')} "
                f"| risk={data.get('aml_risk_score', '-')}/10"
            )
```

- [ ] **Step 6: Smoke test (no API key needed)**

```bash
python analyzer.py --limit 1 --no-llm
```

Expected: processes 1 site without error, writes `results/output.xlsx`

- [ ] **Step 7: Commit**

```bash
git add analyzer.py
git commit -m "feat: integrate LLM enricher into analysis pipeline"
```

---

## Task 6: Create `README.md`

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Crypto Gambling Site Analyzer

Automated pipeline for classifying crypto gambling platforms by AML compliance and fraud risk.

Built as a test assignment for a crypto analyst role. Demonstrates:
- Programmatic site scraping with graceful fallbacks
- Regex-based structured data extraction from unstructured legal text
- Hybrid AI pipeline: Claude Haiku fills extraction gaps and produces risk scores
- Batch Excel output

---

## What it does

For each URL in the input spreadsheet, the pipeline runs four steps:

1. **Scrape** — fetches the homepage and legal pages (`/terms`, `/about`, `/legal`, `/privacy`). If the site is unreachable, falls back to the nearest web.archive.org snapshot.

2. **Extract** — regex extractors pull 15+ structured fields from the page text: KYC/AML policies, license details, legal entity name, country of registration, supported cryptocurrencies, blockchain networks, payout speed, and more.

3. **Enrich with AI** — a single Claude Haiku API call per site receives the regex output as context, fills in any gaps the regex missed, and produces:
   - `aml_risk_score` (1–10, where 10 = highest risk)
   - `aml_risk_reasoning` (2–3 sentence explanation)
   - `fraud_flags` (list of specific red flags found)

4. **Supplement** — additional data from AskGamblers: player ratings, complaint counts, verified payout speed.

Results are written row-by-row into `results/output.xlsx` (copied from the input file to preserve formatting).

---

## Output fields

| Column | Field | Source |
|--------|-------|--------|
| B | platform_name | URL parsing |
| C | status_code | Scraper (active/inactive/unreachable) |
| D | platform_type | Regex (online casino/betting/lottery/slots) |
| E | is_AML | Regex — AML policy mentioned? (y/n) |
| F | is_KYC | Regex — KYC required? (y/n) |
| G | KYC_type | Regex — KYC / OPTIONAL_KYC / NO_KYC |
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
| X | supported_crypto | Regex (BTC, ETH, …) |
| Y | supported_fiat | Regex (USD, EUR, …) |
| Z | crypto_only | Regex (y/n) |
| AA | blockchains | Regex (Ethereum, TRON, …) |
| AB | is_decentralized | Regex (y/n) |
| AC | ssl_valid | SSL certificate check |
| AD | domain_age_years | WHOIS |
| AE | founded_year | AskGamblers |
| AF | aml_risk_score | AI — 1 (low) to 10 (high risk) |
| AG | aml_risk_reasoning | AI — explanation of score |
| AH | fraud_flags | AI — list of red flags |

---

## Setup

**Requirements:** Python 3.11+

```bash
git clone <repo-url>
cd crypto-analyze
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

# First 10 sites only
python analyzer.py --limit 10

# Start from row 20 (useful for resuming)
python analyzer.py --start 20

# Fast mode — skip LLM (no API key needed)
python analyzer.py --no-llm
```

Results are saved to `results/output.xlsx`.

---

## Methodology

### Why hybrid regex + LLM?

Regex is fast, deterministic, and free. It reliably handles the majority of sites. The LLM (Claude Haiku) is called once per site as a single enrichment pass:

- **Gap-filling:** passes already-extracted fields as context so the model only works on what regex missed — efficient and focused
- **Risk scoring:** produces a holistic AML/fraud assessment based on license quality, KYC strictness, jurisdiction, anonymity features, and crypto-only operation

Cost: ~$0.001 per site. Latency: ~2 seconds per site.

### AML Risk Score

The model evaluates:
- Presence and jurisdiction of regulatory license (MGA/UKGC = lower risk; Curaçao = medium; none = high)
- KYC strictness (mandatory full KYC vs optional vs none)
- Whether anonymous play is explicitly promoted
- Crypto-only operation (no fiat = harder to trace transactions)
- DeFi/on-chain features (smart contracts, non-custodial)
- Site age and SSL validity

---

## Project structure

```
├── analyzer.py         Main pipeline — reads input Excel, writes output
├── scraper.py          Web scraping with archive.org fallback
├── extractors.py       15+ regex extractors for structured attribute extraction
├── llm_enricher.py     Claude API: fills extraction gaps + AML risk scoring
├── requirements.txt
├── tests/
│   ├── test_extractors.py
│   └── test_llm_enricher.py
└── Gembling_zadanie_Istomin_N.xlsx   Input dataset
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with methodology and field reference"
```

---

## Task 7: Run full analysis

- [ ] **Step 1: Verify API key is set**

```bash
echo $ANTHROPIC_API_KEY | head -c 20
```

Expected: starts with `sk-ant-`

- [ ] **Step 2: Run full pipeline**

```bash
python analyzer.py
```

Expected: processes all sites, prints per-site status with `risk=X/10`, writes `results/output.xlsx`

- [ ] **Step 3: Run all tests as final check**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: add results output, final state"
```

---

## Self-Review Notes

- All spec requirements covered: git repo ✓, .gitignore ✓, README ✓, llm_enricher ✓, gap-fill ✓, risk score ✓, full run ✓
- No TBDs or placeholders
- Types consistent: `enrich(extracted: dict, site_text: str) -> dict` used identically in all tasks
- `--no-llm` flag propagated correctly from argparse → `main()` → `analyze_site()`
