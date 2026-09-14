from fraudguard.core.config import Settings
from fraudguard.domain.interfaces import FraudModel
from fraudguard.models.predictor import MockFraudModel


def load_model(settings: Settings) -> FraudModel:
    """Called once per worker lifespan. Future registry resolution belongs here."""
    return MockFraudModel()
