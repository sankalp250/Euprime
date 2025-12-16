from dataclasses import dataclass
from typing import Optional, List
import re

HUB_LOCATIONS = [
    "Boston", "Cambridge", "Massachusetts", "Bay Area", "San Francisco", "San Diego",
    "Basel", "Cambridge UK", "Oxford", "London", "Golden Triangle",
]

DILI_KEYWORDS = [
    "drug-induced liver injury",
    "DILI",
    "hepatic toxicity",
    "liver toxicity",
    "investigative toxicology",
    "3D cell culture",
    "organ-on-chip",
    "hepatic spheroids",
    "NAMs",
    "new approach methodologies",
]


@dataclass
class Lead:
    name: str
    title: str
    company: str
    person_location: str
    company_hq: str
    email: Optional[str]
    linkedin_url: Optional[str]
    funding_stage: Optional[str]  # e.g. "Seed", "Series A", "Series B", "Public", "Grant"
    uses_similar_tech: bool       # already working with in-vitro models / organ-on-chip / etc
    open_to_nams: bool            # signals from site / pubs / job posts
    recent_publications: List[str]  # titles of recent papers (last 2 years)
    is_conference_attendee: bool
    is_conference_speaker_or_presenter: bool


def score_role_fit(title: str) -> int:
    title_lower = title.lower()
    score = 0
    if any(k in title_lower for k in ["director", "head", "vp", "vice president", "chief"]):
        score += 10
    if any(k in title_lower for k in ["toxicology", "toxicologist"]):
        score += 20
    if any(k in title_lower for k in ["safety", "preclinical", "nonclinical"]):
        score += 15
    if any(k in title_lower for k in ["hepatic", "liver"]):
        score += 10
    if "3d" in title_lower:
        score += 10
    return min(score, 30)  # cap at +30


def score_company_intent(funding_stage: Optional[str]) -> int:
    if not funding_stage:
        return 0
    stage = funding_stage.lower()
    if "series b" in stage or "series c" in stage:
        return 20
    if "series a" in stage:
        return 15
    if "seed" in stage:
        return 8
    if "ipo" in stage or "public" in stage:
        return 12
    if "grant" in stage:
        return 10
    return 0


def score_technographic(uses_similar_tech: bool, open_to_nams: bool) -> int:
    score = 0
    if uses_similar_tech:
        score += 15
    if open_to_nams:
        score += 10
    return min(score, 25)


def score_location(person_location: str, company_hq: str) -> int:
    locs = f"{person_location} {company_hq}".lower()
    for hub in HUB_LOCATIONS:
        if hub.lower() in locs:
            return 10
    return 0


def score_scientific_intent(publication_titles: List[str]) -> int:
    titles_text = " ".join(publication_titles).lower()
    score = 0
    if any(re.search(r"\b" + re.escape(k.lower()) + r"\b", titles_text) for k in DILI_KEYWORDS):
        score += 30  # strong signal
    if len(publication_titles) >= 2:
        score += 10  # active publishing pattern
    return min(score, 40)


def score_conference_signal(attendee: bool, speaker: bool) -> int:
    if speaker:
        return 15
    if attendee:
        return 8
    return 0


def compute_propensity_score(lead: Lead) -> int:
    role = score_role_fit(lead.title)
    company_int = score_company_intent(lead.funding_stage)
    techno = score_technographic(lead.uses_similar_tech, lead.open_to_nams)
    loc = score_location(lead.person_location, lead.company_hq)
    sci = score_scientific_intent(lead.recent_publications)
    conf = score_conference_signal(lead.is_conference_attendee, lead.is_conference_speaker_or_presenter)

    raw_score = role + company_int + techno + loc + sci + conf
    return max(0, min(raw_score, 100))


def demo_leads() -> List[Lead]:
    """Return a small set of mock leads for the demo dashboard."""
    return [
        Lead(
            name="Alice Smith",
            title="Director of Safety Assessment",
            company="HepatoThera Biotech",
            person_location="Remote - Colorado",
            company_hq="Cambridge, MA",
            email="alice.smith@hepatothera.com",
            linkedin_url="https://www.linkedin.com/in/alicesmith",
            funding_stage="Series B",
            uses_similar_tech=True,
            open_to_nams=True,
            recent_publications=[
                "Drug-induced liver injury assessment using 3D hepatic spheroids",
                "New approach methodologies for investigative toxicology",
            ],
            is_conference_attendee=True,
            is_conference_speaker_or_presenter=True,
        ),
        Lead(
            name="Bob Johnson",
            title="Junior Scientist, Cell Biology",
            company="NanoLiver Startups",
            person_location="Austin, TX",
            company_hq="Austin, TX",
            email="bob.johnson@nanoliver.io",
            linkedin_url="https://www.linkedin.com/in/bobjohnson",
            funding_stage="Pre-seed",
            uses_similar_tech=False,
            open_to_nams=False,
            recent_publications=[],
            is_conference_attendee=False,
            is_conference_speaker_or_presenter=False,
        ),
        Lead(
            name="Carla Gomez",
            title="Head of Investigative Toxicology",
            company="BayBridge Pharma",
            person_location="San Francisco Bay Area",
            company_hq="South San Francisco, CA",
            email="carla.gomez@baybridgepharma.com",
            linkedin_url="https://www.linkedin.com/in/carlagomez",
            funding_stage="Series A",
            uses_similar_tech=True,
            open_to_nams=True,
            recent_publications=[
                "Hepatic toxicity profiling in organ-on-chip models",
            ],
            is_conference_attendee=True,
            is_conference_speaker_or_presenter=False,
        ),
        Lead(
            name="Deepa Nair",
            title="VP Preclinical Development",
            company="Cambridge HepatoTech",
            person_location="Cambridge, MA",
            company_hq="Cambridge, MA",
            email="deepa.nair@hepatotech.com",
            linkedin_url="https://www.linkedin.com/in/deepanair",
            funding_stage="Series C",
            uses_similar_tech=True,
            open_to_nams=True,
            recent_publications=[
                "Organ-on-chip approaches for drug-induced liver injury",
            ],
            is_conference_attendee=True,
            is_conference_speaker_or_presenter=True,
        ),
        Lead(
            name="Ethan Lee",
            title="Director, Investigative Toxicology",
            company="BaySphere Therapeutics",
            person_location="South San Francisco, CA",
            company_hq="South San Francisco, CA",
            email="ethan.lee@baysphere.com",
            linkedin_url="https://www.linkedin.com/in/ethanlee",
            funding_stage="Series B",
            uses_similar_tech=True,
            open_to_nams=True,
            recent_publications=[
                "In-vitro hepatic spheroids for mechanistic toxicity",
            ],
            is_conference_attendee=True,
            is_conference_speaker_or_presenter=False,
        ),
        Lead(
            name="Farah Khan",
            title="Head of Safety Pharmacology",
            company="GoldenTriangle Bio",
            person_location="Oxford, UK",
            company_hq="Oxford, UK",
            email="farah.khan@goldentrianglebio.co.uk",
            linkedin_url="https://www.linkedin.com/in/farahkhan",
            funding_stage="Series A",
            uses_similar_tech=False,
            open_to_nams=True,
            recent_publications=[
                "NAMs in preclinical safety pipelines",
            ],
            is_conference_attendee=False,
            is_conference_speaker_or_presenter=False,
        ),
        Lead(
            name="Gabriel Rossi",
            title="Senior Scientist, DMPK",
            company="Milan Bioinnovations",
            person_location="Milan, Italy",
            company_hq="Milan, Italy",
            email="gabriel.rossi@milanbio.com",
            linkedin_url="https://www.linkedin.com/in/gabrielrossi",
            funding_stage="Seed",
            uses_similar_tech=False,
            open_to_nams=False,
            recent_publications=[],
            is_conference_attendee=False,
            is_conference_speaker_or_presenter=False,
        ),
        Lead(
            name="Hannah Wright",
            title="Director of Nonclinical Safety",
            company="Basel Therapeutics",
            person_location="Basel, Switzerland",
            company_hq="Basel, Switzerland",
            email="hannah.wright@baselthera.com",
            linkedin_url="https://www.linkedin.com/in/hannahwright",
            funding_stage="Series B",
            uses_similar_tech=True,
            open_to_nams=True,
            recent_publications=[
                "Cross-species liver toxicity assessment using 3D cultures",
            ],
            is_conference_attendee=True,
            is_conference_speaker_or_presenter=False,
        ),
        Lead(
            name="Ivan Petrov",
            title="Principal Scientist, Liver Models",
            company="OrganChip Labs",
            person_location="Remote - Colorado",
            company_hq="Boston, MA",
            email="ivan.petrov@organchip.com",
            linkedin_url="https://www.linkedin.com/in/ivanpetrov",
            funding_stage="Series A",
            uses_similar_tech=True,
            open_to_nams=True,
            recent_publications=[
                "Hepatocyte spheroids in NAM workflows",
            ],
            is_conference_attendee=True,
            is_conference_speaker_or_presenter=False,
        ),
    ]
