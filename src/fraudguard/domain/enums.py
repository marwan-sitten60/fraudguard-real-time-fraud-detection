from enum import StrEnum


class Decision(StrEnum):
    APPROVE = "APPROVE"
    MONITOR = "MONITOR"
    REVIEW = "REVIEW"
    CHALLENGE = "CHALLENGE"
    BLOCK = "BLOCK"


class PaymentChannel(StrEnum):
    ONLINE = "ONLINE"
    POS = "POS"
    MOBILE = "MOBILE"
