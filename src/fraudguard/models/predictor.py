from fraudguard.domain.entities import FeatureSnapshot, Prediction, Transaction


class MockFraudModel:
    """Constant 0.23 for plumbing tests only. This is NOT trained or calibrated."""

    version = "mock-v1"
    ready = True

    def predict(self, transaction: Transaction, features: FeatureSnapshot) -> Prediction:
        return Prediction(risk_score=0.23, model_version=self.version)
