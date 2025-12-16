from typing import List, Dict, Any

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from lead_scoring import Lead, compute_propensity_score, demo_leads
from data_sources import fetch_pubmed_authors, generate_biotech_leads_from_funding


class LeadState(BaseModel):
    """State passed through the LangGraph workflow."""

    query: str = Field("", description="Free-text query / keywords, e.g., 'drug-induced liver injury Boston'")
    location_filter: str = Field("", description="Optional location filter, e.g., 'Boston' or 'Cambridge'")
    min_score: int = Field(0, description="Minimum propensity score to include")
    use_live_sources: bool = Field(False, description="If true, call live data providers (PubMed) instead of mock.")
    leads: List[Dict[str, Any]] = Field(default_factory=list, description="Raw leads with scores")


def identify_leads(state: LeadState) -> LeadState:
    """Stage 1: Identification - Gather leads from various sources."""

    collected: List[Lead] = []
    
    if state.use_live_sources:
        # Live PubMed data for researchers/authors publishing on relevant topics
        pubmed_query = state.query or "drug induced liver injury 3D cell culture toxicology"
        pubmed_leads = fetch_pubmed_authors(pubmed_query, limit=15)
        collected.extend(pubmed_leads)
    
    # Always include demo leads + biotech leads for a comprehensive list
    collected.extend(demo_leads())
    collected.extend(generate_biotech_leads_from_funding())

    state.leads = [lead_to_dict(lead) for lead in collected]
    return state


def lead_to_dict(lead: Lead) -> Dict[str, Any]:
    """Convert Lead dataclass to dict with basic info."""
    return {
        "name": lead.name,
        "title": lead.title,
        "company": lead.company,
        "person_location": lead.person_location,
        "company_hq": lead.company_hq,
        "email": lead.email,
        "linkedin_url": lead.linkedin_url,
        "funding_stage": lead.funding_stage,
        "uses_similar_tech": lead.uses_similar_tech,
        "open_to_nams": lead.open_to_nams,
        "recent_publications": lead.recent_publications if isinstance(lead.recent_publications, list) else [],
        "is_conference_attendee": lead.is_conference_attendee,
        "is_conference_speaker_or_presenter": lead.is_conference_speaker_or_presenter,
    }


def enrich_leads(state: LeadState) -> LeadState:
    """Stage 2: Enrichment - Calculate propensity scores and add derived data."""
    
    enriched: List[Dict[str, Any]] = []
    seen_names = set()  # Deduplicate by name
    
    for lead_dict in state.leads:
        name = lead_dict.get("name", "")
        if name in seen_names:
            continue
        seen_names.add(name)
        
        # Reconstruct Lead object for scoring
        lead = Lead(
            name=lead_dict.get("name", "Unknown"),
            title=lead_dict.get("title", ""),
            company=lead_dict.get("company", ""),
            person_location=lead_dict.get("person_location", ""),
            company_hq=lead_dict.get("company_hq", ""),
            email=lead_dict.get("email"),
            linkedin_url=lead_dict.get("linkedin_url"),
            funding_stage=lead_dict.get("funding_stage"),
            uses_similar_tech=lead_dict.get("uses_similar_tech", False),
            open_to_nams=lead_dict.get("open_to_nams", False),
            recent_publications=lead_dict.get("recent_publications", []),
            is_conference_attendee=lead_dict.get("is_conference_attendee", False),
            is_conference_speaker_or_presenter=lead_dict.get("is_conference_speaker_or_presenter", False),
        )
        
        score = compute_propensity_score(lead)
        
        # Format publications for display
        pubs = lead.recent_publications
        pubs_str = "; ".join(pubs) if pubs else ""
        
        enriched.append({
            **lead_dict,
            "recent_publications": pubs_str,
            "propensity_score": score,
        })
    
    state.leads = enriched
    return state


def filter_and_rank(state: LeadState) -> LeadState:
    """Stage 3: Apply filters and sort by propensity score descending."""

    filtered = [
        lead
        for lead in state.leads
        if lead["propensity_score"] >= state.min_score
    ]

    if state.location_filter:
        lf = state.location_filter.lower()
        filtered = [
            lead
            for lead in filtered
            if lf in (lead["person_location"] or "").lower()
            or lf in (lead["company_hq"] or "").lower()
        ]

    if state.query:
        q = state.query.lower()
        filtered = [
            lead
            for lead in filtered
            if q in (lead["title"] or "").lower()
            or q in (lead["company"] or "").lower()
            or q in (lead["recent_publications"] or "").lower()
            or q in (lead["name"] or "").lower()
        ]

    filtered.sort(key=lambda x: x["propensity_score"], reverse=True)
    state.leads = filtered
    return state


def build_workflow():
    """Build the LangGraph workflow for lead generation pipeline."""
    graph = StateGraph(LeadState)
    
    # Add nodes for each stage
    graph.add_node("identify", identify_leads)
    graph.add_node("enrich", enrich_leads)
    graph.add_node("filter_rank", filter_and_rank)

    # Define the workflow edges
    graph.set_entry_point("identify")
    graph.add_edge("identify", "enrich")
    graph.add_edge("enrich", "filter_rank")
    graph.add_edge("filter_rank", END)

    return graph.compile()


if __name__ == "__main__":
    workflow = build_workflow()
    initial = LeadState(query="liver", location_filter="", min_score=0)
    final_state = workflow.invoke(initial.model_dump())
    from pprint import pprint
    
    print(f"\n=== Found {len(final_state['leads'])} leads ===\n")
    for lead in final_state["leads"][:5]:
        print(f"[{lead['propensity_score']:3d}] {lead['name']} - {lead['title']} @ {lead['company']}")
