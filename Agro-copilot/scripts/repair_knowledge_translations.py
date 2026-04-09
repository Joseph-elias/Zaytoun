import json
import re
from pathlib import Path


DATA_PATH = Path("backend/data/olive_knowledge/knowledge_entries.json")

FIELDS = [
    "probable_issue",
    "alternative_causes",
    "why_it_thinks_that",
    "what_to_check_next",
    "safe_actions",
    "when_to_call_agronomist",
    "recommended_followup_questions",
]

AR_RE = re.compile(r"[\u0600-\u06FF]")


ISSUE_AR = {
    "american_plum_borer_issue": "اشتباه ضرر حفار البرقوق الأمريكي",
    "ants_interference": "احتمال تأثير النمل على فعالية المكافحة الحيوية",
    "armillaria_root_rot": "اشتباه تعفن جذور أرميلاريا",
    "botryosphaeria_blight": "اشتباه لفحة/تقرح بوتريوسفيريا",
    "branch_twig_borer_issue": "اشتباه ضرر حفار الأفرع والأغصان",
    "california_red_scale": "اشتباه إصابة بالحشرة القشرية الحمراء",
    "greedy_latania_scale": "اشتباه إصابة بقشرية جريدي/لاتانيا",
    "lebanon_regional_context": "تم تحديد السياق اللبناني (تطبيق عوامل المنطقة والمناخ والصنف)",
    "mycocentrospora_issue": "اشتباه مرض تبقع الأوراق (Mycocentrospora)",
    "nematode_issue": "اشتباه إجهاد جذور مرتبط بالنيماتودا",
    "oleander_scale_issue": "اشتباه إصابة بقشرية الأولياندر على الزيتون",
    "olive_fruit_fly": "اشتباه إصابة بذبابة ثمار الزيتون",
    "olive_psyllid": "اشتباه ضغط بسيلا الزيتون",
    "olive_scale": "اشتباه إصابة بالحشرة القشرية على الزيتون",
    "phytophthora_root_crown_rot": "اشتباه عفن الجذور والتاج بفيتوفثورا",
    "verticillium_wilt": "اشتباه ذبول فيرتيسيليومي",
    "weevils_issue": "اشتباه ضرر سوس التغذية",
    "western_flower_thrips_issue": "اشتباه ضرر التربس الغربي",
    "xylella_fastidiosa_risk": "سياق خطر محتمل لزايليلا فاستيديوزا (ممرض منظم)",
}


GENERIC_AR = {
    "alternative_causes": ["إجهاد غير حيوي", "اختلال تغذوي", "ضغط آخر من آفة أو مرض"],
    "why_it_thinks_that": [
        "نمط الأعراض يتوافق مبدئيًا مع هذه المشكلة.",
        "يلزم التحقق الميداني قبل أي معالجة كبيرة.",
    ],
    "what_to_check_next": [
        "افحص العلامات على عدة أشجار ممثلة في الحقل.",
        "قيّم شدة الإصابة وتوزعها داخل القطعة.",
        "راجع الطقس والري وإدارة البستان الحديثة.",
    ],
    "safe_actions": [
        "عزز المراقبة قبل أي علاج واسع.",
        "أعط الأولوية للنظافة الزراعية والتقليم المناسب.",
        "أكد السبب قبل قرارات علاجية مكلفة.",
    ],
    "when_to_call_agronomist": "تواصل مع مهندس زراعي إذا كان الانتشار سريعًا أو زاد خطر فقدان الإنتاج.",
    "recommended_followup_questions": [
        "متى بدأت الأعراض؟",
        "هل المشكلة موضعية أم منتشرة في الحقل؟",
        "ما التغييرات الزراعية التي حدثت مؤخرًا؟",
    ],
}


LEBANON_AR = {
    "alternative_causes": [
        "تباين المناخ المحلي بين الساحل والداخل",
        "اختلاف القابلية حسب الصنف (مثل الأصناف المحلية)",
        "تداخل الجفاف والحرارة مع إدارة الري",
    ],
    "why_it_thinks_that": [
        "تتوفر مراجع لبنانية للمؤسسات والمخاطر المناخية والسياق الصنفي.",
        "اختلاف المنطقة والمناخ والصنف قد يغيّر تفسير الأعراض وأولوية التدخل.",
    ],
    "what_to_check_next": [
        "سجل المنطقة/القضاء والارتفاع والصنف في القطع المتأثرة.",
        "قارن أمطار وحرارة آخر 30 يومًا مع المعدلات المحلية الموسمية.",
        "راجع سجل الري وسلوك التربة قبل أي قرار معالجة.",
    ],
    "safe_actions": [
        "تجنب خطة معالجة موحدة لكل المناطق اللبنانية.",
        "اعتمد على الطقس المحلي وتاريخ المزرعة وخصائص الصنف قبل أي تدخل كيميائي.",
        "حوّل الحالات غير الواضحة أو المتفاقمة إلى مهندس زراعي محلي.",
    ],
    "when_to_call_agronomist": "تواصل مع مهندس زراعي محلي إذا استمرت الأعراض بعد تعديل إدارة الماء/المناخ أو تسارع الانتشار.",
    "recommended_followup_questions": [
        "في أي منطقة لبنانية وعلى أي ارتفاع يقع البستان؟",
        "ما الصنف المزروع في كل منطقة متأثرة؟",
        "كيف تغيّر المطر والحرارة والري قبل ظهور الأعراض؟",
    ],
}


def _demojibake_text(s: str) -> str:
    try:
        return s.encode("latin1").decode("utf-8")
    except Exception:
        return s


def _demojibake_obj(value: object) -> object:
    if isinstance(value, str):
        return _demojibake_text(value)
    if isinstance(value, list):
        return [_demojibake_obj(x) for x in value]
    if isinstance(value, dict):
        return {k: _demojibake_obj(v) for k, v in value.items()}
    return value


def is_bad_ar(value: object) -> bool:
    if isinstance(value, str):
        return (not value.strip()) or ("?" in value) or (AR_RE.search(value) is None)
    if isinstance(value, list):
        if not value:
            return True
        for item in value:
            if (not isinstance(item, str)) or (not item.strip()) or ("?" in item) or (AR_RE.search(item) is None):
                return True
        return False
    return True


def ensure_fr(value_en: object, value_fr: object) -> object:
    if isinstance(value_fr, str) and value_fr.strip():
        return value_fr
    if isinstance(value_fr, list) and value_fr:
        return value_fr
    return value_en


def main() -> None:
    global ISSUE_AR, GENERIC_AR, LEBANON_AR
    ISSUE_AR = _demojibake_obj(ISSUE_AR)
    GENERIC_AR = _demojibake_obj(GENERIC_AR)
    LEBANON_AR = _demojibake_obj(LEBANON_AR)

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    repaired_entries = 0

    for entry in data:
        eid = entry.get("id", "")
        touched = False

        for field in FIELDS:
            value = entry[field]

            # Keep French complete; if missing, use English fallback.
            value["fr"] = ensure_fr(value.get("en"), value.get("fr"))

            # Repair Arabic only when missing/corrupt.
            if not is_bad_ar(value.get("ar")):
                continue

            touched = True
            if field == "probable_issue":
                value["ar"] = ISSUE_AR.get(eid, "اشتباه مشكلة في الزيتون (بحاجة لتأكيد)")
            elif eid == "lebanon_regional_context":
                value["ar"] = LEBANON_AR[field]
            else:
                value["ar"] = GENERIC_AR[field]

        if touched:
            repaired_entries += 1

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"repaired_entries={repaired_entries}")


if __name__ == "__main__":
    main()
