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
