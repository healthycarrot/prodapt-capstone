"""
Issue #9 – [Pipeline v2] Step 4: 正規表現/NLPによる決定的フィールド抽出

Deterministic field extraction from resume HTML using BeautifulSoup semantic tags,
with regex fallback for whitespace-parsed docs.

Public API
----------
    extract_all_fields(doc: dict) -> ExtractedFields

Classes
-------
    Experience, Education, SkillPhrase, ExtractedFields
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

# ── version ─────────────────────────────────────────────────────

EXTRACTOR_VERSION = "extract_fields_v1.0"

# ── dataclasses ─────────────────────────────────────────────────


@dataclass
class Experience:
    title: str | None = None
    raw_title: str | None = None
    company: str | None = None
    start_date: str | None = None       # ISO yyyy-MM-dd or yyyy-MM or yyyy
    end_date: str | None = None
    is_current: bool = False
    location: str | None = None
    duration_months: int | None = None
    description_raw: str | None = None
    confidence: float = 0.0


@dataclass
class Education:
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    graduation_year: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    confidence: float = 0.0


@dataclass
class SkillPhrase:
    raw_text: str = ""
    source_section: str = ""            # SKLL / HILT / TSKL / CERT


@dataclass
class ExtractedFields:
    name_title: str | None = None
    current_location: str | None = None
    experiences: list[Experience] = field(default_factory=list)
    educations: list[Education] = field(default_factory=list)
    skills: list[SkillPhrase] = field(default_factory=list)
    occupation_candidates: list[str] = field(default_factory=list)
    extraction_method: str = "none"     # "html" | "text" | "none"
    extractor_version: str = EXTRACTOR_VERSION


# ── date utilities ──────────────────────────────────────────────

_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# "Current", "Present", "Now" → treated as is_current
_CURRENT_RE = re.compile(r"^\s*(current|present|now|ongoing|today)\s*$", re.I)

# MM/YYYY
_DATE_MMYYYY = re.compile(r"^(\d{1,2})\s*/\s*(\d{4})$")
# Month YYYY  (e.g. "Dec 2013", "September 2020")
_DATE_MON_YYYY = re.compile(
    r"^(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(\d{4})$",
    re.I,
)
# YYYY alone
_DATE_YYYY = re.compile(r"^(\d{4})$")
# MM-YYYY
_DATE_MM_DASH_YYYY = re.compile(r"^(\d{1,2})\s*-\s*(\d{4})$")


def normalize_date(raw: str | None) -> str | None:
    """Normalize a date string to ISO-ish format.

    Returns yyyy-MM-dd, yyyy-MM, or yyyy depending on precision.
    Returns None if unparseable.
    """
    if not raw:
        return None
    s = raw.strip()
    if not s or _CURRENT_RE.match(s):
        return None

    m = _DATE_MMYYYY.match(s)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1950 <= year <= 2030:
            return f"{year:04d}-{month:02d}"

    m = _DATE_MM_DASH_YYYY.match(s)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1950 <= year <= 2030:
            return f"{year:04d}-{month:02d}"

    m = _DATE_MON_YYYY.match(s)
    if m:
        month_name, year_str = m.group(1).lower(), m.group(2)
        month = _MONTH_MAP.get(month_name[:3])
        year = int(year_str)
        if month and 1950 <= year <= 2030:
            return f"{year:04d}-{month:02d}"

    m = _DATE_YYYY.match(s)
    if m:
        year = int(m.group(1))
        if 1950 <= year <= 2030:
            return f"{year:04d}"

    # Last resort: search for a 4-digit year anywhere in the string
    m = re.search(r"\b((?:19|20)\d{2})\b", s)
    if m:
        year = int(m.group(1))
        if 1950 <= year <= 2030:
            return f"{year:04d}"

    return None


def is_current_marker(raw: str | None) -> bool:
    """Check if a date string indicates 'current/present'."""
    if not raw:
        return False
    return bool(_CURRENT_RE.match(raw.strip()))


def compute_duration_months(
    start: str | None, end: str | None, is_current: bool
) -> int | None:
    """Compute duration in months between two ISO date strings."""
    if not start:
        return None

    try:
        parts_s = start.split("-")
        y_s = int(parts_s[0])
        m_s = int(parts_s[1]) if len(parts_s) > 1 else 1

        if is_current:
            today = date.today()
            y_e, m_e = today.year, today.month
        elif end:
            parts_e = end.split("-")
            y_e = int(parts_e[0])
            m_e = int(parts_e[1]) if len(parts_e) > 1 else 12
        else:
            return None

        months = (y_e - y_s) * 12 + (m_e - m_s)
        return max(0, months)
    except (ValueError, IndexError):
        return None


# ── text helpers ────────────────────────────────────────────────

def _clean(text: str | None) -> str | None:
    """Strip and normalise whitespace; return None if empty."""
    if not text:
        return None
    s = re.sub(r"\s+", " ", text).strip()
    return s if s else None


def _text(tag: Tag | None) -> str | None:
    """Get cleaned text from a BS4 tag."""
    if tag is None:
        return None
    return _clean(tag.get_text())


# ── SECTION finders (in original HTML) ─────────────────────────

def _find_section_divs(soup: BeautifulSoup, section_type: str) -> list[Tag]:
    """Find all <div class='section'> matching a given section type."""
    result = []
    for div in soup.find_all("div", class_="section"):
        sid = div.get("id", "")
        m = re.match(r"^SECTION_([A-Z]+)\d+$", sid)
        if m and m.group(1) == section_type:
            result.append(div)
    return result


# ── EXPERIENCE extraction (HTML) ──────────────────────────────

def extract_experiences_html(soup: BeautifulSoup) -> list[Experience]:
    """Extract experience records from EXPR section HTML."""
    expr_divs = _find_section_divs(soup, "EXPR")
    experiences: list[Experience] = []

    for section_div in expr_divs:
        paragraphs = section_div.find_all("div", class_="paragraph")
        for para in paragraphs:
            exp = _parse_experience_paragraph(para)
            if exp and (exp.title or exp.company or exp.description_raw):
                experiences.append(exp)

    return experiences


def _parse_experience_paragraph(para: Tag) -> Experience | None:
    """Parse a single experience paragraph from HTML."""
    exp = Experience()

    # Job title
    jobtitle_tag = para.find("span", class_="jobtitle")
    if jobtitle_tag:
        raw = _text(jobtitle_tag)
        exp.raw_title = raw
        exp.title = raw

    # Company name
    company_tag = para.find("span", class_="companyname")
    if company_tag:
        exp.company = _text(company_tag)

    # Dates – find all jobdates spans
    date_spans = para.find_all("span", class_="jobdates")
    start_raw, end_raw = None, None
    for span in date_spans:
        span_id = span.get("id", "")
        text = _text(span)
        if not text or text.lower() == "to":
            continue
        if "JSTD" in span_id:
            start_raw = text
        elif "EDDT" in span_id:
            end_raw = text
        elif not start_raw:
            start_raw = text
        else:
            end_raw = text

    if start_raw:
        exp.start_date = normalize_date(start_raw)
    if end_raw:
        if is_current_marker(end_raw):
            exp.is_current = True
            exp.end_date = None
        else:
            exp.end_date = normalize_date(end_raw)

    exp.duration_months = compute_duration_months(
        exp.start_date, exp.end_date, exp.is_current
    )

    # Location
    city_tag = para.find("span", class_="jobcity")
    state_tag = para.find("span", class_="jobstate")
    city = _text(city_tag)
    state = _text(state_tag)
    if city and state:
        exp.location = f"{city}, {state}"
    elif city:
        exp.location = city
    elif state:
        exp.location = state

    # Description
    desc_tag = para.find("span", attrs={"itemprop": "description"})
    if not desc_tag:
        desc_tag = para.find("span", class_="jobline")
    if desc_tag:
        exp.description_raw = _text(desc_tag)

    # Confidence
    filled = sum(1 for v in [exp.title, exp.company, exp.start_date,
                              exp.description_raw] if v)
    exp.confidence = round(filled / 4, 2)

    return exp


# ── EXPERIENCE extraction (text fallback) ─────────────────────

# Simpler split: look for date-range boundaries
_MONTHS_PAT = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)
_DATE_PAT = rf"(?:\d{{1,2}}/\d{{4}}|(?:{_MONTHS_PAT})\s+\d{{4}})"
_DATE_RANGE_BOUNDARY = re.compile(
    rf"({_DATE_PAT})\s+to\s+({_DATE_PAT}|Current|Present)",
    re.I,
)

# City, State pattern
_CITY_STATE_RE = re.compile(
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,\s*([A-Z]{2}|[A-Z][a-z]+)"
)


def extract_experiences_text(text: str) -> list[Experience]:
    """Fallback: extract experience from plain text using regex."""
    if not text:
        return []

    # Split on date range boundaries
    matches = list(_DATE_RANGE_BOUNDARY.finditer(text))
    if not matches:
        # Return the entire text as one experience block
        return [Experience(
            description_raw=_clean(text),
            confidence=0.1,
        )]

    experiences: list[Experience] = []
    for i, m in enumerate(matches):
        # Text before the date range contains the title
        block_start = matches[i - 1].end() if i > 0 else 0
        prefix = text[block_start:m.start()].strip()

        # Text after the date range until next match is the description
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        suffix = text[m.end():block_end].strip()

        start_raw = m.group(1)
        end_raw = m.group(2)
        is_curr = is_current_marker(end_raw)

        # Extract title from prefix (last line or capitalized phrase)
        title = _clean(prefix.split("\n")[-1]) if prefix else None

        # Extract location from suffix
        loc = None
        loc_m = _CITY_STATE_RE.search(suffix[:100])
        if loc_m:
            loc = f"{loc_m.group(1)}, {loc_m.group(2)}"

        start_iso = normalize_date(start_raw)
        end_iso = None if is_curr else normalize_date(end_raw)

        exp = Experience(
            title=title,
            raw_title=title,
            start_date=start_iso,
            end_date=end_iso,
            is_current=is_curr,
            location=loc,
            duration_months=compute_duration_months(start_iso, end_iso, is_curr),
            description_raw=_clean(suffix),
            confidence=0.3,
        )
        experiences.append(exp)

    return experiences


# ── EDUCATION extraction (HTML) ───────────────────────────────

def extract_educations_html(soup: BeautifulSoup) -> list[Education]:
    """Extract education records from EDUC section HTML."""
    educ_divs = _find_section_divs(soup, "EDUC")
    educations: list[Education] = []

    for section_div in educ_divs:
        paragraphs = section_div.find_all("div", class_="paragraph")
        for para in paragraphs:
            edu = _parse_education_paragraph(para)
            if edu and (edu.institution or edu.degree or edu.field_of_study):
                educations.append(edu)

    return educations


def _parse_education_paragraph(para: Tag) -> Education | None:
    """Parse a single education paragraph from HTML."""
    edu = Education()

    # Degree
    degree_tag = para.find("span", class_="degree")
    if degree_tag:
        edu.degree = _text(degree_tag)

    # Field of study (programline)
    program_tag = para.find("span", class_="programline")
    if program_tag:
        edu.field_of_study = _text(program_tag)

    # Institution (companyname_educ or SCHO id)
    inst_tag = para.find("span", class_="companyname_educ")
    if not inst_tag:
        inst_tag = para.find("span", class_="companyname")
    if inst_tag:
        edu.institution = _text(inst_tag)

    # Graduation year – look for GRYR in id
    for span in para.find_all("span", class_="jobdates"):
        span_id = span.get("id", "")
        text = _text(span)
        if "GRYR" in span_id and text:
            # Might be "2014" or "05/2005"
            edu.graduation_year = text
            norm = normalize_date(text)
            if norm:
                edu.end_date = norm
            break

    # Location
    city_tag = para.find("span", class_="jobcity")
    if not city_tag:
        city_tag = para.find("span", class_="educity")
    state_tag = para.find("span", class_="jobstate")
    if not state_tag:
        state_tag = para.find("span", class_="edustate")
    country_tag = para.find("span", class_="eduCountry")

    parts = []
    city = _text(city_tag)
    state = _text(state_tag)
    country = _text(country_tag)
    if city:
        parts.append(city)
    if state:
        parts.append(state)
    if country:
        parts.append(country)
    if parts:
        edu.location = ", ".join(parts)

    # Confidence
    filled = sum(1 for v in [edu.institution, edu.degree,
                              edu.field_of_study, edu.graduation_year] if v)
    edu.confidence = round(filled / 4, 2)

    return edu


# ── EDUCATION extraction (text fallback) ──────────────────────

_DEGREE_RE = re.compile(
    r"((?:Doctor(?:ate)?|Ph\.?D|Master(?:'s)?|M\.?[BSFA]\.?[ACS]?|"
    r"Bachelor(?:'s)?|B\.?[BSFA]\.?[ACS]?|Associate(?:'s)?|"
    r"High\s+School\s+Diploma|Certificate(?:\s+of\s+Completion)?|Diploma|"
    r"M\.?Ed|M\.?P\.?H|J\.?D|M\.?D|D\.?O|Ed\.?D)"
    r"(?:\s+(?:of|in)\s+[A-Za-z]+(?:\s+[A-Za-z]+){0,4})?)",
    re.I,
)

_INSTITUTION_RE = re.compile(
    r"([A-Z][A-Za-z'\-.]+(?:\s+[A-Za-z'\-.]+){0,6}\s+"
    r"(?:University|College|Institute|School|Academy|Polytechnic))",
    re.I,
)

_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def extract_educations_text(text: str) -> list[Education]:
    """Fallback: extract education from plain text using regex."""
    if not text:
        return []

    # Try to split on degree keywords or year boundaries
    blocks: list[str] = []
    degree_matches = list(_DEGREE_RE.finditer(text))

    if degree_matches:
        for i, dm in enumerate(degree_matches):
            start = dm.start()
            end = degree_matches[i + 1].start() if i + 1 < len(degree_matches) else len(text)
            blocks.append(text[start:end])
    else:
        blocks = [text]

    educations: list[Education] = []
    for block in blocks:
        edu = Education()

        dm = _DEGREE_RE.search(block)
        if dm:
            edu.degree = _clean(dm.group(1))

        im = _INSTITUTION_RE.search(block)
        if im:
            edu.institution = _clean(im.group(1))

        ym = _YEAR_RE.search(block)
        if ym:
            edu.graduation_year = ym.group(1)
            edu.end_date = ym.group(1)

        # Location
        loc_m = _CITY_STATE_RE.search(block)
        if loc_m:
            edu.location = f"{loc_m.group(1)}, {loc_m.group(2)}"

        # Field of study: after degree "in/of/:" pattern
        fos_m = re.search(
            r"(?:in|of|:)\s+([A-Z][A-Za-z &]+(?:\s+[A-Za-z &]+){0,4})",
            block,
        )
        if fos_m:
            edu.field_of_study = _clean(fos_m.group(1))

        filled = sum(1 for v in [edu.institution, edu.degree,
                                  edu.field_of_study, edu.graduation_year] if v)
        edu.confidence = round(filled / 4 * 0.6, 2)  # lower confidence for text

        if edu.institution or edu.degree:
            educations.append(edu)

    return educations


# ── SKILLS extraction ─────────────────────────────────────────

# Delimiters for skill phrase splitting
_SKILL_SPLIT_RE = re.compile(r"[,;|•·●◦▪►➤\n]+")

# Noise phrases to filter out
_SKILL_NOISE = {
    "", "and", "or", "the", "a", "an", "in", "of", "to", "for",
    "with", "on", "at", "from", "by", "as", "etc", "other",
}

# Section types that contain skills
_SKILL_SECTION_TYPES = {"SKLL", "HILT", "TSKL", "CERT"}


def extract_skills_from_text(text: str, source_section: str) -> list[SkillPhrase]:
    """Split skill text into individual phrases."""
    if not text:
        return []

    phrases = _SKILL_SPLIT_RE.split(text)
    result: list[SkillPhrase] = []
    seen: set[str] = set()

    for phrase in phrases:
        cleaned = re.sub(r"\s+", " ", phrase).strip()
        # Remove leading bullets/dashes
        cleaned = re.sub(r"^[\-\*\u2022\u2023\u25e6\u2043\u2219]\s*", "", cleaned)
        normalized = cleaned.lower()

        if (
            not cleaned
            or normalized in _SKILL_NOISE
            or len(cleaned) < 2
            or len(cleaned) > 100
            or normalized in seen
        ):
            continue

        seen.add(normalized)
        result.append(SkillPhrase(
            raw_text=cleaned,
            source_section=source_section,
        ))

    return result


def extract_skills(
    parsed_sections: list[dict[str, Any]] | None,
) -> list[SkillPhrase]:
    """Extract skill phrases from all skill-related sections."""
    if not parsed_sections:
        return []

    all_skills: list[SkillPhrase] = []
    for sec in parsed_sections:
        stype = sec.get("section_type", "")
        if stype in _SKILL_SECTION_TYPES:
            text = sec.get("text", "")
            all_skills.extend(extract_skills_from_text(text, stype))

    return all_skills


# ── NAME / TITLE / LOCATION extraction ────────────────────────

def extract_name_title(
    parsed_sections: list[dict[str, Any]] | None,
) -> str | None:
    """Extract the job title from NAME section."""
    if not parsed_sections:
        return None

    for sec in parsed_sections:
        if sec.get("section_type") == "NAME":
            title = _clean(sec.get("text", ""))
            if title and len(title) < 100:
                return title

    return None


def extract_current_location_html(soup: BeautifulSoup) -> str | None:
    """Extract current location from the first EXPR block's City, State."""
    expr_divs = _find_section_divs(soup, "EXPR")
    for section_div in expr_divs:
        # First paragraph = most recent job
        para = section_div.find("div", class_="paragraph")
        if not para:
            continue
        city_tag = para.find("span", class_="jobcity")
        state_tag = para.find("span", class_="jobstate")
        city = _text(city_tag)
        state = _text(state_tag)
        if city and state and city.lower() != "city" and state.lower() != "state":
            return f"{city}, {state}"
    return None


def extract_current_location_text(text: str | None) -> str | None:
    """Fallback: extract City, State from text."""
    if not text:
        return None
    m = _CITY_STATE_RE.search(text)
    if m:
        city, state = m.group(1), m.group(2)
        if city.lower() != "city" and state.lower() != "state":
            return f"{city}, {state}"
    return None


# ── OCCUPATION CANDIDATES ──────────────────────────────────────

def collect_occupation_candidates(
    name_title: str | None,
    experiences: list[Experience],
) -> list[str]:
    """Collect unique occupation title candidates from NAME + EXPR titles."""
    seen: set[str] = set()
    result: list[str] = []

    # 1. NAME section title (highest priority)
    if name_title:
        norm = name_title.strip()
        if norm.lower() not in seen:
            seen.add(norm.lower())
            result.append(norm)

    # 2. Experience titles
    for exp in experiences:
        if exp.title:
            norm = exp.title.strip()
            if norm.lower() not in seen:
                seen.add(norm.lower())
                result.append(norm)

    return result


# ── MAIN DISPATCHER ───────────────────────────────────────────

def extract_all_fields(doc: dict[str, Any]) -> ExtractedFields:
    """Extract all deterministic fields from a single resume document.

    Uses HTML semantic tags when available, falls back to regex on plain text.

    Parameters
    ----------
    doc : dict
        MongoDB document with at least:
        - resume_html (str)
        - resume_text (str)
        - parsed_sections (list[dict])
        - parsing_method (str)

    Returns
    -------
    ExtractedFields
    """
    result = ExtractedFields()
    resume_html = doc.get("resume_html", "") or ""
    parsed_sections = doc.get("parsed_sections") or []
    parsing_method = doc.get("parsing_method", "none")

    if parsing_method == "none" or not parsed_sections:
        result.extraction_method = "none"
        return result

    # ── HTML path (primary) ──────────────────────────────────
    if parsing_method == "html" and resume_html:
        soup = BeautifulSoup(resume_html, "html.parser")
        result.extraction_method = "html"

        # Experiences
        result.experiences = extract_experiences_html(soup)

        # Education
        result.educations = extract_educations_html(soup)

        # Location from first EXPR block
        result.current_location = extract_current_location_html(soup)

    # ── Text path (fallback) ─────────────────────────────────
    else:
        result.extraction_method = "text"

        # Find EXPR section text
        expr_text = ""
        educ_text = ""
        for sec in parsed_sections:
            if sec.get("section_type") == "EXPR":
                expr_text += " " + sec.get("text", "")
            elif sec.get("section_type") == "EDUC":
                educ_text += " " + sec.get("text", "")

        result.experiences = extract_experiences_text(expr_text.strip())
        result.educations = extract_educations_text(educ_text.strip())
        result.current_location = extract_current_location_text(expr_text)

    # ── Common (both paths) ──────────────────────────────────

    # Name / title
    result.name_title = extract_name_title(parsed_sections)

    # Skills (always from parsed_sections text, splitting is delimiter-based)
    result.skills = extract_skills(parsed_sections)

    # Occupation candidates
    result.occupation_candidates = collect_occupation_candidates(
        result.name_title, result.experiences
    )

    return result


# ── Serialization helpers ──────────────────────────────────────

def fields_to_dict(ef: ExtractedFields) -> dict[str, Any]:
    """Convert ExtractedFields to a plain dict for MongoDB storage."""
    return {
        "name_title": ef.name_title,
        "current_location": ef.current_location,
        "experiences": [asdict(e) for e in ef.experiences],
        "educations": [asdict(e) for e in ef.educations],
        "skills": [asdict(s) for s in ef.skills],
        "occupation_candidates": ef.occupation_candidates,
        "extraction_method": ef.extraction_method,
        "extractor_version": ef.extractor_version,
    }


def compute_fill_rates(ef: ExtractedFields) -> dict[str, float]:
    """Compute per-field fill rates for a single document."""
    rates: dict[str, float] = {}

    rates["name_title"] = 1.0 if ef.name_title else 0.0
    rates["current_location"] = 1.0 if ef.current_location else 0.0
    rates["has_experiences"] = 1.0 if ef.experiences else 0.0
    rates["has_educations"] = 1.0 if ef.educations else 0.0
    rates["has_skills"] = 1.0 if ef.skills else 0.0
    rates["has_occupation_candidates"] = 1.0 if ef.occupation_candidates else 0.0

    if ef.experiences:
        n = len(ef.experiences)
        rates["exp_title"] = sum(1 for e in ef.experiences if e.title) / n
        rates["exp_company"] = sum(1 for e in ef.experiences if e.company) / n
        rates["exp_start_date"] = sum(1 for e in ef.experiences if e.start_date) / n
        rates["exp_end_date_or_current"] = sum(
            1 for e in ef.experiences if e.end_date or e.is_current
        ) / n
        rates["exp_location"] = sum(1 for e in ef.experiences if e.location) / n
        rates["exp_description"] = sum(
            1 for e in ef.experiences if e.description_raw
        ) / n
        rates["exp_avg_confidence"] = sum(
            e.confidence for e in ef.experiences
        ) / n

    if ef.educations:
        n = len(ef.educations)
        rates["edu_institution"] = sum(1 for e in ef.educations if e.institution) / n
        rates["edu_degree"] = sum(1 for e in ef.educations if e.degree) / n
        rates["edu_field_of_study"] = sum(
            1 for e in ef.educations if e.field_of_study
        ) / n
        rates["edu_graduation_year"] = sum(
            1 for e in ef.educations if e.graduation_year
        ) / n
        rates["edu_avg_confidence"] = sum(
            e.confidence for e in ef.educations
        ) / n

    rates["skill_count"] = float(len(ef.skills))

    return rates
