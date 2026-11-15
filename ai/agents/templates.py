"""Deterministic replies in the request language, built only from tool evidence."""

from __future__ import annotations

from typing import Any

_TEXT: dict[str, dict[str, str]] = {
    "unsupported_candidate": {
        "en": "I can help find jobs that match your profile. Other requests are not supported yet.",
        "fr": "Je peux vous aider à trouver des offres d'emploi adaptées à votre profil. "
        "Les autres demandes ne sont pas encore prises en charge.",
        "ar": "يمكنني مساعدتك في العثور على وظائف تناسب ملفك الشخصي. الطلبات الأخرى غير مدعومة بعد.",
    },
    "candidate_has_no_skills": {
        "en": "Add skills to your profile to find matching job offers.",
        "fr": "Ajoutez des compétences à votre profil pour trouver des offres correspondantes.",
        "ar": "أضف مهارات إلى ملفك الشخصي للعثور على عروض عمل مطابقة.",
    },
    "no_matching_offers": {
        "en": "No published offers matched your request.",
        "fr": "Aucune offre publiée ne correspond à votre demande.",
        "ar": "لا توجد عروض منشورة تطابق طلبك.",
    },
    "personalise_hint": {
        "en": "Add skills to your profile for personalised results.",
        "fr": "Ajoutez des compétences à votre profil pour des résultats personnalisés.",
        "ar": "أضف مهارات إلى ملفك الشخصي للحصول على نتائج مخصصة.",
    },
    "offer": {
        "en": "{rank}. {title} at {organization}.",
        "fr": "{rank}. {title} chez {organization}.",
        "ar": "{rank}. {title} لدى {organization}.",
    },
    "matched": {
        "en": "Matched skills: {skills}.",
        "fr": "Compétences correspondantes : {skills}.",
        "ar": "المهارات المتوفرة: {skills}.",
    },
    "missing": {
        "en": "Missing skills: {skills}.",
        "fr": "Compétences manquantes : {skills}.",
        "ar": "المهارات الناقصة: {skills}.",
    },
    "training": {
        "en": "Training for missing skills: {programs}.",
        "fr": "Formations pour les compétences manquantes : {programs}.",
        "ar": "تكوينات للمهارات الناقصة: {programs}.",
    },
    "program": {
        "en": "{title} ({organization}) for {skill}",
        "fr": "{title} ({organization}) pour {skill}",
        "ar": "{title} ({organization}) لمهارة {skill}",
    },
    "link": {
        "en": "Offer link: {url}",
        "fr": "Lien de l'offre : {url}",
        "ar": "رابط العرض: {url}",
    },
    "none": {"en": "none", "fr": "aucune", "ar": "لا شيء"},
    "no_cv_analysis": {
        "en": "Run an ATS analysis of one of your CVs in “Mes CV”, then I can tell you what to "
        "improve first.",
        "fr": "Lancez une analyse ATS d'un de vos CV dans « Mes CV » : je pourrai ensuite vous "
        "dire quoi améliorer en priorité.",
        "ar": "أطلق تحليل ATS لإحدى سيرك الذاتية في « Mes CV »، ثم يمكنني أن أخبرك بما يجب "
        "تحسينه أولاً.",
    },
    "cv_analysis": {
        "en": "Your latest ATS analysis ({cv} v{version}, {role}) scores {score}/100. "
        "Improve first:",
        "fr": "Votre dernière analyse ATS ({cv} v{version}, {role}) donne {score}/100. "
        "À améliorer en priorité :",
        "ar": "آخر تحليل ATS لسيرتك ({cv} v{version}، {role}) يعطي {score}/100. حسّن أولاً:",
    },
    "cv_hint": {
        "en": "Open “Mes CV” to apply these fixes and re-run the analysis.",
        "fr": "Ouvrez « Mes CV » pour appliquer ces corrections et relancer l'analyse.",
        "ar": "افتح « Mes CV » لتطبيق هذه التصحيحات وإعادة التحليل.",
    },
    "unsupported_recruiter": {
        "en": "I can help find opted-in candidate profiles and search your offers. "
        "Other requests are not supported yet.",
        "fr": "Je peux vous aider à trouver des profils de candidats visibles et à rechercher "
        "vos offres. Les autres demandes ne sont pas encore prises en charge.",
        "ar": "يمكنني مساعدتك في العثور على ملفات المرشحين المتاحة والبحث في عروضك. "
        "الطلبات الأخرى غير مدعومة بعد.",
    },
    "no_matching_profiles": {
        "en": "No visible candidate profiles matched your request.",
        "fr": "Aucun profil de candidat visible ne correspond à votre demande.",
        "ar": "لا توجد ملفات مرشحين متاحة تطابق طلبك.",
    },
    "offer_not_accessible": {
        "en": "This offer is not accessible from your account.",
        "fr": "Cette offre n'est pas accessible depuis votre compte.",
        "ar": "هذا العرض غير متاح من حسابك.",
    },
    "profile": {
        "en": "Profile {rank}. Matched skills: {skills}.",
        "fr": "Profil n°{rank}. Compétences correspondantes : {skills}.",
        "ar": "الملف رقم {rank}. المهارات المطابقة: {skills}.",
    },
    "profiles_hint": {
        "en": "Open a profile from the sources below to see its details.",
        "fr": "Ouvrez un profil depuis les sources ci-dessous pour voir ses détails.",
        "ar": "افتح ملفاً من المصادر أدناه لعرض تفاصيله.",
    },
    "recruiter_has_no_offers": {
        "en": "Your organization has no offers yet.",
        "fr": "Votre organisation n'a pas encore d'offres.",
        "ar": "لا توجد عروض لمؤسستك بعد.",
    },
    "no_matching_own_offers": {
        "en": "None of your offers matched your request.",
        "fr": "Aucune de vos offres ne correspond à votre demande.",
        "ar": "لا يطابق أي من عروضك طلبك.",
    },
    "own_offer": {
        "en": "{rank}. {title} ({status}). Skills: {skills}.",
        "fr": "{rank}. {title} ({status}). Compétences : {skills}.",
        "ar": "{rank}. {title} ({status}). المهارات: {skills}.",
    },
}
_STATUS: dict[str, dict[str, str]] = {
    "DRAFT": {"en": "draft", "fr": "brouillon", "ar": "مسودة"},
    "PUBLISHED": {"en": "published", "fr": "publiée", "ar": "منشور"},
    "PAUSED": {"en": "paused", "fr": "suspendue", "ar": "متوقف"},
    "CLOSED": {"en": "closed", "fr": "clôturée", "ar": "مغلق"},
    "ARCHIVED": {"en": "archived", "fr": "archivée", "ar": "مؤرشف"},
}
_LIST_SEPARATOR: dict[str, str] = {"en": ", ", "fr": ", ", "ar": "، "}


def text(key: str, language: str, **values: Any) -> str:
    return _TEXT[key][language].format(**values)


def unsupported_reply(language: str, role: str = "candidate") -> str:
    return text(f"unsupported_{role}", language)


def _listed(names: list[str], language: str) -> str:
    return _LIST_SEPARATOR[language].join(names) or text("none", language)


def cv_advice_reply(evidence: dict[str, Any], language: str) -> str:
    """Score and stored issue messages of the latest analysis; nothing is generated."""
    if evidence["reason"] != "analysis_found":
        return text(evidence["reason"], language)
    header = text(
        "cv_analysis",
        language,
        cv=evidence["cv_title"],
        version=evidence["cv_version"],
        role=evidence["role"],
        score=evidence["score"],
    )
    return "\n".join([header, *(f"- {point}" for point in evidence["points"])]) + (
        "\n" + text("cv_hint", language)
    )


def candidate_search_reply(evidence: dict[str, Any], language: str) -> str:
    """Ranks and matched skills only: the profile link is in the citations, never its text."""
    if not evidence["matches"]:
        return text(evidence["reason"], language)
    lines = [
        text(
            "profile",
            language,
            rank=rank,
            skills=_listed(match["matched_skills"], language),
        )
        for rank, match in enumerate(evidence["matches"], 1)
    ]
    lines.append(text("profiles_hint", language))
    return "\n".join(lines)


def own_offer_search_reply(evidence: dict[str, Any], language: str) -> str:
    if not evidence["matches"]:
        reason = evidence["reason"]
        return text(
            "no_matching_own_offers" if reason == "no_matching_offers" else reason, language
        )
    return "\n".join(
        text(
            "own_offer",
            language,
            rank=rank,
            title=match["title"],
            status=_STATUS.get(match["status"], {}).get(language, match["status"].lower()),
            skills=_listed(match["skills"], language),
        )
        for rank, match in enumerate(evidence["matches"], 1)
    )


def job_search_reply(evidence: dict[str, Any], language: str) -> str:
    if not evidence["matches"]:
        return text(evidence["reason"], language)
    lines = []
    for rank, match in enumerate(evidence["matches"], 1):
        parts = [
            text(
                "offer",
                language,
                rank=rank,
                title=match["title"],
                organization=match["organization"],
            ),
            text("matched", language, skills=_listed(match["matched_skills"], language)),
            text("missing", language, skills=_listed(match["missing_skills"], language)),
        ]
        if match["training"]:
            programs = "; ".join(
                text("program", language, **program) for program in match["training"]
            )
            parts.append(text("training", language, programs=programs))
        if match["offer_url"]:
            parts.append(text("link", language, url=match["offer_url"]))
        lines.append(" ".join(parts))
    if not evidence["profile_has_skills"]:
        lines.append(text("personalise_hint", language))
    return "\n".join(lines)
