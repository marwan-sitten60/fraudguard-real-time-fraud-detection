from fraudguard.domain.entities import FeatureSnapshot, RuleResult, Transaction


class BasicRuleEngine:
    """Illustrative signal only; it does not force a block or modify mock scores."""

    def evaluate(self, transaction: Transaction, features: FeatureSnapshot) -> RuleResult:
        codes = ("COUNTRY_MISMATCH",) if transaction.country != transaction.ip_country else ()
        return RuleResult(reason_codes=codes)
