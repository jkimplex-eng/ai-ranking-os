"""Supported research geographies and their natural-language query context."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchGeography:
    code: str
    label: str
    query_context_ru: str
    query_context_en: str


RUSSIAN_GEOGRAPHIES: tuple[ResearchGeography, ...] = (
    ResearchGeography("RU", "Вся Россия", "по всей России", "across Russia"),
    ResearchGeography("RU-MOW", "Москва", "в Москве", "in Moscow"),
    ResearchGeography(
        "RU-SPE", "Санкт-Петербург", "в Санкт-Петербурге", "in Saint Petersburg"
    ),
    ResearchGeography("RU-NVS", "Новосибирск", "в Новосибирске", "in Novosibirsk"),
    ResearchGeography("RU-SVE", "Екатеринбург", "в Екатеринбурге", "in Yekaterinburg"),
    ResearchGeography("RU-TA", "Казань", "в Казани", "in Kazan"),
    ResearchGeography("RU-KYA", "Красноярск", "в Красноярске", "in Krasnoyarsk"),
    ResearchGeography(
        "RU-NIZ", "Нижний Новгород", "в Нижнем Новгороде", "in Nizhny Novgorod"
    ),
    ResearchGeography("RU-CHE", "Челябинск", "в Челябинске", "in Chelyabinsk"),
    ResearchGeography("RU-BA", "Уфа", "в Уфе", "in Ufa"),
    ResearchGeography("RU-SAM", "Самара", "в Самаре", "in Samara"),
    ResearchGeography(
        "RU-ROS", "Ростов-на-Дону", "в Ростове-на-Дону", "in Rostov-on-Don"
    ),
    ResearchGeography("RU-KDA", "Краснодар", "в Краснодаре", "in Krasnodar"),
    ResearchGeography("RU-OMS", "Омск", "в Омске", "in Omsk"),
    ResearchGeography("RU-VOR", "Воронеж", "в Воронеже", "in Voronezh"),
    ResearchGeography("RU-PER", "Пермь", "в Перми", "in Perm"),
    ResearchGeography("RU-VGG", "Волгоград", "в Волгограде", "in Volgograd"),
)

_BY_CODE = {item.code: item for item in RUSSIAN_GEOGRAPHIES}


def geography(code: str) -> ResearchGeography | None:
    """Return a supported Russian geography without rejecting legacy regions."""

    return _BY_CODE.get(code.upper())


def geography_label(code: str) -> str:
    item = geography(code)
    return item.label if item else code


def query_context(code: str, *, english: bool) -> str:
    item = geography(code)
    if item is None:
        return ""
    return item.query_context_en if english else item.query_context_ru
