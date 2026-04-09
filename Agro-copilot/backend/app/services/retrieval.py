import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from backend.app.models.diagnosis import SupportedLanguage


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "olive_knowledge"


@dataclass(frozen=True)
class SourceRecord:
    id: str
    title: str
    url: str
    publisher: str
    accessed_on: str
    trust_level: str


@dataclass(frozen=True)
class KnowledgeEntry:
    id: str
    keywords: tuple[str, ...]
    category: str
    subcategory: str
    probable_issue: dict[str, str]
    confidence_hint: str
    urgency_hint: str
    alternative_causes: dict[str, list[str]]
    why_it_thinks_that: dict[str, list[str]]
    what_to_check_next: dict[str, list[str]]
    safe_actions: dict[str, list[str]]
    when_to_call_agronomist: dict[str, str]
    recommended_followup_questions: dict[str, list[str]]
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class RetrievedCase:
    entry: KnowledgeEntry
    score: int


@dataclass(frozen=True)
class KnowledgeBundle:
    entries: tuple[KnowledgeEntry, ...]
    sources_by_id: dict[str, SourceRecord]


def _load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_ontology() -> dict:
    return _load_json(DATA_DIR / "ontology.json")


def get_classifier_policies() -> dict:
    ontology = load_ontology()
    return ontology.get("classifier_policies", {})


def get_classifier_mapping(label: str) -> dict | None:
    normalized = " ".join(label.lower().split())
    ontology = load_ontology()
    rows = ontology.get("classifier_label_mapping", [])
    for row in rows:
        canonical = str(row.get("label", "")).lower().strip()
        aliases = [str(a).lower().strip() for a in row.get("aliases", [])]
        if normalized == canonical or normalized in aliases:
            return row
    return None


@lru_cache(maxsize=1)
def load_knowledge_bundle() -> KnowledgeBundle:
    source_rows = _load_json(DATA_DIR / "sources.json")
    entry_rows = _load_json(DATA_DIR / "knowledge_entries.json")

    sources_by_id = {
        row["id"]: SourceRecord(
            id=row["id"],
            title=row["title"],
            url=row["url"],
            publisher=row["publisher"],
            accessed_on=row["accessed_on"],
            trust_level=row["trust_level"],
        )
        for row in source_rows
    }

    entries = []
    for row in entry_rows:
        entries.append(
            KnowledgeEntry(
                id=row["id"],
                keywords=tuple(row["keywords"]),
                category=row.get("category", "management"),
                subcategory=row.get("subcategory", "general"),
                probable_issue=row["probable_issue"],
                confidence_hint=row["confidence_hint"],
                urgency_hint=row["urgency_hint"],
                alternative_causes=row["alternative_causes"],
                why_it_thinks_that=row["why_it_thinks_that"],
                what_to_check_next=row["what_to_check_next"],
                safe_actions=row["safe_actions"],
                when_to_call_agronomist=row["when_to_call_agronomist"],
                recommended_followup_questions=row["recommended_followup_questions"],
                source_ids=tuple(row["source_ids"]),
            )
        )

    return KnowledgeBundle(entries=tuple(entries), sources_by_id=sources_by_id)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "disease": (
        "disease", "infection", "fungus", "fungal", "bacterial", "spot", "wilt", "rot", "canker", "???", "???", "????"
    ),
    "pest": (
        "pest", "insect", "mite", "fly", "scale", "thrips", "weevil", "nematode", "???", "????", "??", "?????"
    ),
    "climate": (
        "weather", "climate", "frost", "freeze", "heatwave", "drought", "rainfall", "stress", "???", "????", "????", "??", "????"
    ),
    "management": (
        "pruning", "irrigation", "fertilizer", "fertigation", "harvest", "pollination", "soil", "salinity", "ph", "?????", "??", "?????", "????"
    ),
    "economics": (
        "cost", "price", "profit", "market", "roi", "income", "economic", "?????", "???", "???", "???"
    ),
}


def detect_intent_categories(text: str) -> set[str]:
    normalized = _normalize(text)
    matched: set[str] = set()
    for category, words in INTENT_KEYWORDS.items():
        if any(word in normalized for word in words):
            matched.add(category)
    return matched


def retrieve_cases(text: str, top_k: int = 3) -> list[RetrievedCase]:
    normalized = _normalize(text)
    bundle = load_knowledge_bundle()
    intent_categories = detect_intent_categories(text)

    scored: list[RetrievedCase] = []
    for entry in bundle.entries:
        score = 0
        for keyword in entry.keywords:
            if keyword.lower() in normalized:
                score += 1

        # Boost entries that align with detected intent category.
        if intent_categories and entry.category in intent_categories:
            score += 2

        if score > 0:
            scored.append(RetrievedCase(entry=entry, score=score))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


def build_evidence_sources(retrieved: list[RetrievedCase]) -> list[dict[str, str]]:
    bundle = load_knowledge_bundle()
    source_ids_seen: set[str] = set()
    resolved: list[dict[str, str]] = []

    for row in retrieved:
        for source_id in row.entry.source_ids:
            if source_id in source_ids_seen:
                continue
            source = bundle.sources_by_id.get(source_id)
            if source is None:
                continue
            source_ids_seen.add(source_id)
            resolved.append(
                {
                    "source_id": source.id,
                    "title": source.title,
                    "url": source.url,
                    "publisher": source.publisher,
                    "accessed_on": source.accessed_on,
                    "trust_level": source.trust_level,
                }
            )

    return resolved


def localize_map_text(data: dict[str, str], language: SupportedLanguage) -> str:
    return data.get(language) or data.get("en") or ""


def localize_map_list(data: dict[str, list[str]], language: SupportedLanguage) -> list[str]:
    return data.get(language) or data.get("en") or []

