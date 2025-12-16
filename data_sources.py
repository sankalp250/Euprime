import os
import csv
from typing import List, Optional
from pathlib import Path

import httpx  # pyright: ignore[reportMissingImports]

from lead_scoring import Lead


def load_funded_companies(csv_path: Optional[str] = None) -> List[dict]:
    """Load funded companies from CSV file for enrichment.
    
    Returns a list of company dicts with funding information.
    """
    if csv_path is None:
        csv_path = Path(__file__).parent / "Recently Funded Startups - Sheet1.csv"
    
    companies = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append({
                    'company': row.get('Company', ''),
                    'domain': row.get('Domain', ''),
                    'amount': row.get('Amount (USD)', ''),
                    'round': row.get('Round', ''),
                    'investors': row.get('Investors', ''),
                    'country': row.get('Country', ''),
                    'date': row.get('Date Announced', ''),
                })
    except Exception:
        pass
    return companies


def fetch_pubmed_authors(query: str, limit: int = 10) -> List[Lead]:
    """Fetch recent PubMed authors for the query.

    This uses the free NCBI E-Utilities. We parse author list + affiliation
    to create leads tagged as researchers with publication signals.
    """
    if not query:
        return []

    esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    efetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    leads: List[Lead] = []
    try:
        # Search for recent papers (last 2 years)
        search_query = f"{query} AND (\"2023\"[Date - Publication] OR \"2024\"[Date - Publication] OR \"2025\"[Date - Publication])"
        search_resp = httpx.get(
            esearch,
            params={
                "db": "pubmed",
                "retmode": "json",
                "term": search_query,
                "sort": "date",
                "retmax": limit,
            },
            timeout=20,
        )
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        fetch_resp = httpx.get(
            efetch,
            params={
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "xml",
            },
            timeout=20,
        )
        fetch_resp.raise_for_status()
        xml = fetch_resp.text

        # Parse XML to extract authors and their publications
        import re

        article_chunks = re.findall(r"<PubmedArticle>(.*?)</PubmedArticle>", xml, re.DOTALL)
        seen_names = set()  # Avoid duplicates
        
        for chunk in article_chunks:
            # Get article title
            title_match = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", chunk, re.DOTALL)
            title = title_match.group(1) if title_match else "Recent publication"
            title = re.sub(r'<[^>]+>', '', title)  # Strip HTML tags
            
            # Get publication year
            year_match = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>.*?</PubDate>", chunk, re.DOTALL)
            pub_year = year_match.group(1) if year_match else "2024"
            
            # Get authors - focus on first and corresponding authors
            authors = re.findall(r"<Author[^>]*>(.*?)</Author>", chunk, re.DOTALL)
            
            for i, author in enumerate(authors[:3]):  # Take first 3 authors max per paper
                last = re.search(r"<LastName>(.*?)</LastName>", author)
                fore = re.search(r"<ForeName>(.*?)</ForeName>", author)
                aff = re.search(r"<Affiliation>(.*?)</Affiliation>", author)
                
                name = " ".join(filter(None, [
                    fore.group(1) if fore else None, 
                    last.group(1) if last else None
                ])) or "Unknown Author"
                
                if name in seen_names or name == "Unknown Author":
                    continue
                seen_names.add(name)
                
                affiliation = aff.group(1) if aff else "Research Institution"
                affiliation = re.sub(r'<[^>]+>', '', affiliation)  # Strip HTML
                
                # Determine location from affiliation
                location = ""
                if any(loc in affiliation.lower() for loc in ["boston", "cambridge", "massachusetts", "ma"]):
                    location = "Boston, MA"
                elif any(loc in affiliation.lower() for loc in ["san francisco", "bay area", "california", "ca"]):
                    location = "San Francisco, CA"
                elif any(loc in affiliation.lower() for loc in ["basel", "switzerland"]):
                    location = "Basel, Switzerland"
                elif any(loc in affiliation.lower() for loc in ["oxford", "cambridge uk", "london", "uk", "england"]):
                    location = "United Kingdom"
                elif affiliation:
                    # Try to extract location from end of affiliation
                    loc_parts = affiliation.split(',')
                    if len(loc_parts) >= 2:
                        location = ', '.join(loc_parts[-2:]).strip()[:50]
                
                # Determine role based on author position
                if i == 0:
                    role = "First Author / Researcher"
                else:
                    role = "Corresponding Author / PI" if i == len(authors) - 1 else "Researcher / Author"
                
                leads.append(
                    Lead(
                        name=name,
                        title=role,
                        company=affiliation[:100] if affiliation else "Research Institution",
                        person_location=location or "Unknown",
                        company_hq=location or "Unknown",
                        email=None,
                        linkedin_url=None,
                        funding_stage="Grant",
                        uses_similar_tech=True,  # Publishing in this area = using similar tech
                        open_to_nams=True,
                        recent_publications=[f"{title} ({pub_year})"],
                        is_conference_attendee=False,
                        is_conference_speaker_or_presenter=False,
                    )
                )
    except Exception as e:
        print(f"PubMed fetch error: {e}")
        return []

    return leads


def generate_biotech_leads_from_funding() -> List[Lead]:
    """Generate mock leads based on funded biotech companies.
    
    Creates realistic lead profiles for biotech-relevant funded startups.
    """
    # Biotech/health-tech relevant companies from funding data
    biotech_profiles = [
        {
            "name": "Dr. Sarah Chen",
            "title": "Director of Safety Assessment",
            "company": "Iambic Therapeutics",
            "person_location": "San Diego, CA",
            "company_hq": "San Diego, CA",
            "funding_stage": "Series B",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["AI-driven drug discovery and safety assessment (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": True,
        },
        {
            "name": "Michael Torres, PhD",
            "title": "VP of Preclinical Development",
            "company": "Cassidy Bio",
            "person_location": "Tel Aviv, Israel",
            "company_hq": "Tel Aviv, Israel",
            "funding_stage": "Seed",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["Novel approaches in antibody drug discovery (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": False,
        },
        {
            "name": "Dr. Emily Watson",
            "title": "Head of Investigative Toxicology",
            "company": "QSimulate",
            "person_location": "Boston, MA",
            "company_hq": "Boston, MA",
            "funding_stage": "Seed",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["Quantum simulation for drug toxicity prediction (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": True,
        },
        {
            "name": "James Park",
            "title": "Senior Scientist, DMPK",
            "company": "Neros Technologies",
            "person_location": "Remote - Colorado",
            "company_hq": "Cambridge, MA",
            "funding_stage": "Series B",
            "uses_similar_tech": False,
            "open_to_nams": True,
            "recent_publications": [],
            "is_conference_attendee": False,
            "is_conference_speaker_or_presenter": False,
        },
        {
            "name": "Dr. Anna Kowalski",
            "title": "Director of Liver Models",
            "company": "OrganTech Pharma",
            "person_location": "Basel, Switzerland",
            "company_hq": "Basel, Switzerland",
            "funding_stage": "Series A",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["3D hepatic spheroids for DILI assessment (2024)", "Organ-on-chip liver toxicity models (2023)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": True,
        },
        {
            "name": "Dr. Robert Kim",
            "title": "Chief Scientific Officer",
            "company": "HepaVitro Labs",
            "person_location": "Cambridge, MA",
            "company_hq": "Cambridge, MA",
            "funding_stage": "Series C",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["Drug-induced liver injury prediction using 3D models (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": True,
        },
        {
            "name": "Lisa Martinez",
            "title": "Principal Scientist, Hepatic Safety",
            "company": "Pfizer",
            "person_location": "Groton, CT",
            "company_hq": "New York, NY",
            "funding_stage": "Public",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["NAMs in pharmaceutical safety assessment (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": False,
        },
        {
            "name": "Dr. Thomas Brown",
            "title": "Head of Preclinical Safety",
            "company": "Novartis",
            "person_location": "Basel, Switzerland",
            "company_hq": "Basel, Switzerland",
            "funding_stage": "Public",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["In-vitro hepatotoxicity screening advances (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": True,
        },
        {
            "name": "Jennifer Liu",
            "title": "Associate Director, Toxicology",
            "company": "Genentech",
            "person_location": "South San Francisco, CA",
            "company_hq": "South San Francisco, CA",
            "funding_stage": "Public",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["3D cell culture applications in oncology safety (2023)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": False,
        },
        {
            "name": "Dr. David Miller",
            "title": "VP Nonclinical Development",
            "company": "Regeneron",
            "person_location": "Tarrytown, NY",
            "company_hq": "Tarrytown, NY",
            "funding_stage": "Public",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": [],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": False,
        },
        {
            "name": "Dr. Maria Santos",
            "title": "Director of In-Vitro Models",
            "company": "BioTissue Dynamics",
            "person_location": "London, UK",
            "company_hq": "Cambridge, UK",
            "funding_stage": "Series A",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["Hepatic spheroid models for drug screening (2024)", "Microphysiological systems in toxicology (2023)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": True,
        },
        {
            "name": "Kevin Zhang",
            "title": "Scientist II, Cell Biology",
            "company": "StartupLiver Inc",
            "person_location": "Austin, TX",
            "company_hq": "Austin, TX",
            "funding_stage": "Pre-seed",
            "uses_similar_tech": False,
            "open_to_nams": False,
            "recent_publications": [],
            "is_conference_attendee": False,
            "is_conference_speaker_or_presenter": False,
        },
        {
            "name": "Dr. Rachel Green",
            "title": "Head of Safety Pharmacology",
            "company": "AstraZeneca",
            "person_location": "Cambridge, UK",
            "company_hq": "Cambridge, UK",
            "funding_stage": "Public",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["Alternative methods in safety pharmacology (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": True,
        },
        {
            "name": "Alex Thompson",
            "title": "Research Associate, Toxicology",
            "company": "ToxiScreen Labs",
            "person_location": "Durham, NC",
            "company_hq": "Research Triangle, NC",
            "funding_stage": "Seed",
            "uses_similar_tech": False,
            "open_to_nams": True,
            "recent_publications": [],
            "is_conference_attendee": False,
            "is_conference_speaker_or_presenter": False,
        },
        {
            "name": "Dr. Hiroshi Tanaka",
            "title": "Director of DMPK",
            "company": "Tokyo Pharma Research",
            "person_location": "Tokyo, Japan",
            "company_hq": "Tokyo, Japan",
            "funding_stage": "Series B",
            "uses_similar_tech": True,
            "open_to_nams": True,
            "recent_publications": ["Hepatocyte models for metabolism studies (2024)"],
            "is_conference_attendee": True,
            "is_conference_speaker_or_presenter": False,
        },
    ]
    
    leads = []
    for profile in biotech_profiles:
        leads.append(Lead(
            name=profile["name"],
            title=profile["title"],
            company=profile["company"],
            person_location=profile["person_location"],
            company_hq=profile["company_hq"],
            email=f"{profile['name'].lower().replace(' ', '.').replace(',', '').replace('.', '')}@{profile['company'].lower().replace(' ', '')}.com"[:50],
            linkedin_url=f"https://linkedin.com/in/{profile['name'].lower().replace(' ', '-').replace(',', '').replace('.', '')}",
            funding_stage=profile["funding_stage"],
            uses_similar_tech=profile["uses_similar_tech"],
            open_to_nams=profile["open_to_nams"],
            recent_publications=profile["recent_publications"],
            is_conference_attendee=profile["is_conference_attendee"],
            is_conference_speaker_or_presenter=profile["is_conference_speaker_or_presenter"],
        ))
    
    return leads
