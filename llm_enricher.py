"""
llm_enricher.py — Claude API enrichment for crypto gambling site analysis.

Single API call per site:
  - Fills fields that regex left empty
  - Produces AML risk score (1-10) + reasoning + fraud flags
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
