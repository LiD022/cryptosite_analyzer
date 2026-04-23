"""
extractors.py — извлечение атрибутов из текста сайта с помощью regex и эвристик.

Покрывает:
  - platform_type
  - is_AML / is_KYC / KYC_type
  - license, legal_entity_name, company_reg_country
  - supported_currencies, blockchains, is_decentralized
  - payout_speed_days, games_count
"""

import re


# ---------------------------------------------------------------------------
# Platform type
# ---------------------------------------------------------------------------

PLATFORM_KEYWORDS = {
    "betting": [
        r"\bsportsbook\b", r"\bsport.{0,5}bet", r"\bbetting\b", r"\bodds\b",
        r"\bwagering\b", r"\bfootball.{0,10}bet", r"\bbet.{0,5}sport",
    ],
    "lottery": [
        r"\blottery\b", r"\blotto\b", r"\bticket.{0,5}win",
        r"\bjackpot.{0,10}draw",
    ],
    "online casino": [
        r"\bcasino\b", r"\blive.{0,5}dealer", r"\broulette\b", r"\bblackjack\b",
        r"\bbaccarat\b", r"\bpoker\b", r"\btable.{0,5}game",
    ],
    "online slot machine": [
        r"\bslot.{0,5}machine\b", r"\bslots?\b", r"\bspin.{0,5}reel",
        r"\bfruit.{0,5}machine\b", r"\bpokie\b",
    ],
}


def detect_platform_type(text: str) -> str:
    text_lower = text.lower()
    scores: dict[str, int] = {k: 0 for k in PLATFORM_KEYWORDS}
    for platform, patterns in PLATFORM_KEYWORDS.items():
        for pattern in patterns:
            scores[platform] += len(re.findall(pattern, text_lower))
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "other"


# ---------------------------------------------------------------------------
# AML / KYC
# ---------------------------------------------------------------------------

AML_PATTERNS = [
    r"\baml\b", r"\banti.{0,5}money.{0,5}laundering\b",
    r"\bmoney.{0,5}laundering\b", r"\bfinancial.{0,5}crime\b",
    r"\bsuspicious.{0,5}activit",
]

KYC_PATTERNS = [
    r"\bkyc\b", r"\bknow.{0,5}your.{0,5}customer\b",
    r"\bidentity.{0,5}verif", r"\bpassport.{0,5}verif",
    r"\bdocument.{0,5}verif", r"\bage.{0,5}verif",
]

OPTIONAL_KYC_PATTERNS = [
    r"\bkyc.{0,30}optional\b", r"\boptional.{0,30}kyc\b",
    r"\bno.{0,5}kyc.{0,5}required\b", r"\bkyc.{0,30}not.{0,5}required\b",
    r"\bwithout.{0,10}verif", r"\banonymous.{0,10}(play|gambl|bet)",
]

NO_KYC_PATTERNS = [
    r"\bno.{0,5}kyc\b", r"\bkyc.{0,5}free\b",
    r"\bno.{0,10}id.{0,10}required\b", r"\bplay.{0,10}anonymous",
    r"\bno.{0,5}identity\b",
]


def detect_aml(text: str) -> str:
    text_lower = text.lower()
    return "y" if any(re.search(p, text_lower) for p in AML_PATTERNS) else "n"


def detect_kyc(text: str) -> tuple[str, str]:
    text_lower = text.lower()
    for p in NO_KYC_PATTERNS:
        if re.search(p, text_lower):
            return "n", "NO_KYC"
    for p in OPTIONAL_KYC_PATTERNS:
        if re.search(p, text_lower):
            return "y", "OPTIONAL_KYC"
    for p in KYC_PATTERNS:
        if re.search(p, text_lower):
            return "y", "KYC"
    return "n", "NO_KYC"


# ---------------------------------------------------------------------------
# License
# ---------------------------------------------------------------------------

LICENSE_PATTERNS = [
    r"licen[sc]e[d]?\s*(?:number|no\.?|#)?\s*[:\-]?\s*([A-Z0-9/\-]{4,30})",
    r"(?:gaming|gambling).{0,20}licen[sc]e[d]?\s*(?:by|from|under)?\s*(.{5,60}?)(?:\.|,|\n)",
    r"regulated\s*by\s*(.{5,80}?)(?:\.|,|\n)",
    r"authorised\s*by\s*(.{5,80}?)(?:\.|,|\n)",
    r"licensed\s*(?:and\s*regulated\s*)?by\s*(.{5,80}?)(?:\.|,|\n)",
    r"(?:MGA|UKGC|Cura[çc]ao|Kahnawake|Gibraltar|Isle of Man|Malta Gaming Authority)[^.]{0,60}",
]


def detect_license(text: str) -> list[str]:
    found = []
    for pattern in LICENSE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend([m.strip() for m in matches if len(m.strip()) > 3])
    seen, unique = set(), []
    for item in found:
        key = item.lower()[:40]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:5]


# ---------------------------------------------------------------------------
# Legal entity / registration country
# ---------------------------------------------------------------------------

LEGAL_ENTITY_PATTERNS = [
    # "operated by Foo B.V." — приоритетный паттерн
    r"(?:owned|operated|managed|run)\s*by\s+([A-Z][A-Za-z0-9\s&.,]+?(?:Ltd\.?|LLC\.?|Inc\.?|N\.V\.|B\.V\.|GmbH|S\.A\.|L\.L\.C\.))(?:\s|,|\.|$)",
    # "incorporated in X under Foo B.V."
    r"incorporat\w+\s+(?:in\s+\w+\s+(?:as|under)\s+)?([A-Z][A-Za-z0-9\s&.,]+?(?:Ltd\.?|LLC\.?|Inc\.?|N\.V\.|B\.V\.|GmbH|S\.A\.))(?:\s|,|\.|$)",
    # copyright строка
    r"copyright\s*©?\s*\d{4}[-–]?\d*\s+([A-Z][A-Za-z\s&.,]+?)(?:\.|,|\n|all rights)",
    # широкий паттерн как fallback
    r"([A-Z][A-Za-z\s&.]+?(?:Ltd\.?|LLC\.?|Inc\.?|N\.V\.|B\.V\.|GmbH|S\.A\.))",
]

# Привязываем страну к конкретным регистрационным паттернам, а не просто упоминаниям
COUNTRY_REGISTRATION_PATTERNS = {
    "Curacao":     [r"incorporat\w+\s+in\s+Cura[çc]ao", r"registered\s+in\s+Cura[çc]ao",
                    r"Cura[çc]ao\s+Chamber", r"Willemstad", r"Cura[çc]ao\s+Gaming"],
    "Malta":       [r"incorporat\w+\s+in\s+Malta", r"registered\s+in\s+Malta",
                    r"Malta\s+(?:Business\s+)?Registry", r"MGA\s+licen"],
    "Gibraltar":   [r"incorporat\w+\s+in\s+Gibraltar", r"registered\s+in\s+Gibraltar",
                    r"Gibraltar\s+Gambling\s+Commissioner"],
    "Isle of Man": [r"Isle of Man", r"incorporat\w+\s+in\s+(?:the\s+)?Isle"],
    "UK":          [r"incorporat\w+\s+in\s+(?:England|UK|United Kingdom)",
                    r"Companies House", r"UKGC\s+licen", r"UK Gambling Commission"],
    "Kahnawake":   [r"Kahnawake\s+Gaming", r"Mohawk Territory"],
    "Antigua":     [r"incorporat\w+\s+in\s+Antigua", r"Antigua.*Barbuda\s+licen"],
    "Estonia":     [r"incorporat\w+\s+in\s+Estonia", r"Estonian.*licen"],
    "Sweden":      [r"incorporat\w+\s+in\s+Sweden", r"Spelinspektionen"],
    "United States": [r"incorporat\w+\s+in\s+(?:the\s+)?(?:US|USA|United States)",
                      r"Delaware\s+LLC", r"registered\s+agent.*(?:US|USA)"],
}


def detect_legal_entity(text: str) -> str | None:
    for pattern in LEGAL_ENTITY_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def detect_reg_country(text: str) -> str | None:
    """Определяет страну регистрации по специфичным паттернам регистрации (не просто упоминания)."""
    for country, patterns in COUNTRY_REGISTRATION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return country
    return None


# ---------------------------------------------------------------------------
# Cryptocurrencies & blockchains
# ---------------------------------------------------------------------------

CRYPTO_CURRENCIES = {
    "BTC": [r"\bBTC\b", r"\bBitcoin\b"],
    "ETH": [r"\bETH\b", r"\bEthereum\b"],
    "LTC": [r"\bLTC\b", r"\bLitecoin\b"],
    "USDT": [r"\bUSDT\b", r"\bTether\b"],
    "USDC": [r"\bUSDC\b"],
    "BNB": [r"\bBNB\b", r"\bBinance Coin\b"],
    "XRP": [r"\bXRP\b", r"\bRipple\b"],
    "SOL": [r"\bSOL\b", r"\bSolana\b"],
    "DOGE": [r"\bDOGE\b", r"\bDogecoin\b"],
    "TRX": [r"\bTRX\b", r"\bTRON\b"],
    "ADA": [r"\bADA\b", r"\bCardano\b"],
    "DOT": [r"\bDOT\b", r"\bPolkadot\b"],
    "MATIC": [r"\bMATIC\b", r"\bPolygon\b"],
}

FIAT_CURRENCIES = {
    "USD": [r"\bUSD\b", r"\bUS\s*dollar", r"\bAmerican\s+dollar"],
    "EUR": [r"\bEUR\b", r"\beuro\b"],
    "GBP": [r"\bGBP\b", r"\bpound\b"],
    "JPY": [r"\bJPY\b", r"\byen\b"],
}

BLOCKCHAIN_NETWORKS = {
    "Bitcoin":   [r"\bBitcoin\s+(?:network|blockchain|chain)\b", r"\bBTC\s+network\b"],
    "Ethereum":  [r"\bEthereum\s+(?:network|blockchain|chain)\b", r"\bERC.?20\b", r"\bEVM\b"],
    "Solana":    [r"\bSolana\s+(?:network|blockchain|chain)\b", r"\bSPL\s+token\b"],
    "TRON":      [r"\bTRON\s+(?:network|blockchain|chain)\b", r"\bTRC.?20\b"],
    "BNB Chain": [r"\bBSC\b", r"\bBNB\s+(?:Smart\s+)?Chain\b", r"\bBEP.?20\b"],
    "Polygon":   [r"\bPolygon\s+(?:network|blockchain|chain)\b", r"\bMATIC\s+network\b"],
    "Avalanche": [r"\bAvalanche\b", r"\bAVAX\b"],
    "Arbitrum":  [r"\bArbitrum\b"],
    "Optimism":  [r"\bOptimism\b"],
}


def detect_currencies(text: str) -> dict:
    """Возвращает {'crypto': [...], 'fiat': [...], 'crypto_only': bool}"""
    found_crypto, found_fiat = [], []
    for name, patterns in CRYPTO_CURRENCIES.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            found_crypto.append(name)
    for name, patterns in FIAT_CURRENCIES.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            found_fiat.append(name)
    return {
        "supported_crypto": ", ".join(found_crypto) if found_crypto else None,
        "supported_fiat": ", ".join(found_fiat) if found_fiat else None,
        "crypto_only": "y" if found_crypto and not found_fiat else ("n" if found_fiat else None),
    }


def detect_blockchains(text: str) -> str | None:
    found = []
    for name, patterns in BLOCKCHAIN_NETWORKS.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            found.append(name)
    return ", ".join(found) if found else None


# ---------------------------------------------------------------------------
# Decentralized / DeFi detection
# ---------------------------------------------------------------------------

DEFI_PATTERNS = [
    r"\bdecentrali[sz]ed\b",
    r"\bDeFi\b",
    r"\bsmart\s+contract\b",
    r"\bon.chain\b",
    r"\bDAO\b",
    r"\bweb3\b",
    r"\bnon.custodial\b",
    r"\bself.custodial\b",
    r"\bblockchain.based\s+(?:casino|game|platform)\b",
]

CENTRALIZED_PATTERNS = [
    r"\bcentrali[sz]ed\b",
    r"\bour\s+platform\s+(?:is\s+)?(?:licensed|regulated)\b",
    r"\bcustomer\s+support\b",
    r"\bwithdrawal\s+(?:request|process)\b",
]


def detect_is_decentralized(text: str) -> str | None:
    text_lower = text.lower()
    defi_score = sum(1 for p in DEFI_PATTERNS if re.search(p, text_lower))
    central_score = sum(1 for p in CENTRALIZED_PATTERNS if re.search(p, text_lower))
    if defi_score == 0 and central_score == 0:
        return None
    return "y" if defi_score > central_score else "n"


# ---------------------------------------------------------------------------
# Payout speed & games count
# ---------------------------------------------------------------------------

PAYOUT_PATTERNS = [
    r"payout.{0,20}(?:within|in|up to|takes?)\s*([0-9]+(?:\.[0-9]+)?\s*(?:hours?|days?|minutes?))",
    r"withdrawal.{0,30}(?:within|in|up to|takes?)\s*([0-9]+(?:\.[0-9]+)?\s*(?:hours?|days?|minutes?))",
    r"([0-9]+(?:\.[0-9]+)?\s*(?:hours?|days?))\s*(?:payout|withdrawal|processing)",
    r"instant\s+(?:payout|withdrawal)",
]

GAMES_COUNT_PATTERNS = [
    r"([0-9][0-9,]+)\s*\+?\s*(?:casino\s+)?games?\b",
    r"over\s+([0-9][0-9,]+)\s+(?:casino\s+)?games?\b",
    r"([0-9][0-9,]+)\s*\+?\s*slots?\b",
    r"library\s+of\s+([0-9][0-9,]+)\b",
]


def detect_payout_speed(text: str) -> str | None:
    text_lower = text.lower()
    for pattern in PAYOUT_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            if "instant" in m.group(0):
                return "instant"
            return m.group(1).strip()
    return None


def detect_games_count(text: str) -> str | None:
    for pattern in GAMES_COUNT_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).replace(",", "")
    return None


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

def extract_all(text: str, status: str = "active", archive_url: str | None = None) -> dict:
    """Извлекает все атрибуты из текста страниц сайта."""
    is_kyc, kyc_type = detect_kyc(text)
    licenses = detect_license(text)
    currencies = detect_currencies(text)

    return {
        "status_code": status,
        "platform_type": detect_platform_type(text),
        "is_AML": detect_aml(text),
        "is_KYC": is_kyc,
        "KYC_type": kyc_type,
        "legal_entity_name": detect_legal_entity(text),
        "company_reg_country": detect_reg_country(text),
        "license": "; ".join(licenses) if licenses else None,
        "web_archive_url": archive_url,
        # Новые атрибуты
        "supported_crypto": currencies["supported_crypto"],
        "supported_fiat": currencies["supported_fiat"],
        "crypto_only": currencies["crypto_only"],
        "blockchains": detect_blockchains(text),
        "is_decentralized": detect_is_decentralized(text),
        "payout_speed": detect_payout_speed(text),
        "games_count": detect_games_count(text),
    }


if __name__ == "__main__":
    sample = """
    Roobet is operated by Raw Entertainment B.V., a company incorporated in Curacao
    under license 8048/JAZ. We are fully licensed and regulated by the Curacao
    Gaming Authority. We take AML and KYC compliance seriously. All players must
    complete identity verification before withdrawing funds. We accept Bitcoin (BTC),
    Ethereum (ETH), Litecoin (LTC) and USDT. We use Ethereum blockchain (ERC-20 tokens).
    We offer over 2,000 casino games including slots, live dealer, and sports betting.
    Payouts are processed within 24 hours. We are a centralized platform licensed
    and regulated by the Curacao Gaming Authority.
    """
    result = extract_all(sample)
    for k, v in result.items():
        print(f"{k:25} {v}")
