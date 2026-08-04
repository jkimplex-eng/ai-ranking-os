from enum import StrEnum


class EntityType(StrEnum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PRODUCT = "PRODUCT"
    BRAND = "BRAND"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    DATE = "DATE"
    TIME = "TIME"
    MONEY = "MONEY"
    PERCENTAGE = "PERCENTAGE"
    QUANTITY = "QUANTITY"
    TECHNOLOGY = "TECHNOLOGY"
    DOCUMENT = "DOCUMENT"
    URL = "URL"
    EMAIL = "EMAIL"
    OTHER = "OTHER"


def parse_entity_type(value: object) -> EntityType:
    if isinstance(value, EntityType):
        return value
    normalized = str(value or "OTHER").upper().replace(" ", "_")
    aliases = {
        "ORG": "ORGANIZATION",
        "COMPANY": "ORGANIZATION",
        "GPE": "LOCATION",
        "PLACE": "LOCATION",
        "PERCENT": "PERCENTAGE",
        "TECH": "TECHNOLOGY",
        "URL_ADDRESS": "URL",
        "EMAIL_ADDRESS": "EMAIL",
    }
    normalized = aliases.get(normalized, normalized)
    try:
        return EntityType(normalized)
    except ValueError:
        return EntityType.OTHER

