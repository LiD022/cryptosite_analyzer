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
    extracted = {k: None for k in FIELDS_TO_FILL}
    payload = {"aml_risk_score": 3, "aml_risk_reasoning": "Low risk.", "fraud_flags": []}
    wrapped = f"```json\n{json.dumps(payload)}\n```"
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=wrapped)]
    with patch("llm_enricher.client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        result = enrich(extracted, "some text")
    assert result["aml_risk_score"] == 3


def test_enrich_returns_empty_on_api_error():
    extracted = {k: None for k in FIELDS_TO_FILL}
    with patch("llm_enricher.client") as mock_client:
        mock_client.messages.create.side_effect = Exception("API error")
        result = enrich(extracted, "some text")
    assert result == {}
