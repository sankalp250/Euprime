import io

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from graph_app import build_workflow, LeadState
from lead_scoring import demo_leads
from data_sources import generate_biotech_leads_from_funding


# Page configuration
st.set_page_config(
    page_title="3D In-Vitro Lead Scoring Demo",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .score-high {
        background-color: #10b981;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .score-medium {
        background-color: #f59e0b;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .score-low {
        background-color: #ef4444;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    .database-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🧪 3D In-Vitro Lead Generation & Scoring</h1>', unsafe_allow_html=True)
st.markdown('''<p class="subtitle">
AI-powered lead identification, enrichment, and propensity scoring for 3D in-vitro model partnerships.
Targeting Toxicology, Safety Assessment, and Drug Discovery professionals.
</p>''', unsafe_allow_html=True)

# Main tabs - Database first so users can see the data
main_tab1, main_tab2 = st.tabs(["📊 Lead Scoring Dashboard", "🗃️ Database View"])

with main_tab2:
    st.subheader("🗃️ Lead Database")
    st.info("Browse and search the complete lead database before running the scoring pipeline.")
    
    # Load all leads for database view
    all_leads = demo_leads() + generate_biotech_leads_from_funding()
    
    # Convert to DataFrame
    db_data = []
    for lead in all_leads:
        db_data.append({
            "Name": lead.name,
            "Title": lead.title,
            "Company": lead.company,
            "Person Location": lead.person_location,
            "Company HQ": lead.company_hq,
            "Email": lead.email or "N/A",
            "LinkedIn": lead.linkedin_url or "N/A",
            "Funding Stage": lead.funding_stage or "Unknown",
            "Uses 3D/In-Vitro": "✅" if lead.uses_similar_tech else "❌",
            "Open to NAMs": "✅" if lead.open_to_nams else "❌",
            "Publications": "; ".join(lead.recent_publications) if lead.recent_publications else "None",
            "Conference Attendee": "✅" if lead.is_conference_attendee else "❌",
            "Speaker/Presenter": "✅" if lead.is_conference_speaker_or_presenter else "❌",
        })
    
    db_df = pd.DataFrame(db_data)
    
    # Search functionality
    st.markdown("### 🔍 Search Database")
    col_search1, col_search2, col_search3 = st.columns(3)
    
    with col_search1:
        db_search = st.text_input(
            "Search by keyword",
            placeholder="e.g., toxicology, liver, Boston, Pfizer",
            key="db_search"
        )
    
    with col_search2:
        funding_filter = st.multiselect(
            "Filter by Funding Stage",
            options=db_df["Funding Stage"].unique().tolist(),
            key="funding_filter"
        )
    
    with col_search3:
        tech_filter = st.selectbox(
            "Uses 3D/In-Vitro Tech",
            options=["All", "Yes", "No"],
            key="tech_filter"
        )
    
    # Apply filters
    filtered_db = db_df.copy()
    
    if db_search:
        search_lower = db_search.lower()
        mask = filtered_db.apply(
            lambda row: any(search_lower in str(val).lower() for val in row), 
            axis=1
        )
        filtered_db = filtered_db[mask]
    
    if funding_filter:
        filtered_db = filtered_db[filtered_db["Funding Stage"].isin(funding_filter)]
    
    if tech_filter == "Yes":
        filtered_db = filtered_db[filtered_db["Uses 3D/In-Vitro"] == "✅"]
    elif tech_filter == "No":
        filtered_db = filtered_db[filtered_db["Uses 3D/In-Vitro"] == "❌"]
    
    # Display stats
    st.markdown(f"**Showing {len(filtered_db)} of {len(db_df)} leads**")
    
    # Display database table
    st.dataframe(
        filtered_db,
        use_container_width=True,
        hide_index=True,
        height=500,
    )
    
    # Database summary
    st.markdown("---")
    st.subheader("📈 Database Summary")
    
    summary_cols = st.columns(5)
    with summary_cols[0]:
        st.metric("Total Leads", len(db_df))
    with summary_cols[1]:
        tech_count = len(db_df[db_df["Uses 3D/In-Vitro"] == "✅"])
        st.metric("Using 3D Tech", tech_count)
    with summary_cols[2]:
        nams_count = len(db_df[db_df["Open to NAMs"] == "✅"])
        st.metric("Open to NAMs", nams_count)
    with summary_cols[3]:
        with_pubs = len(db_df[db_df["Publications"] != "None"])
        st.metric("With Publications", with_pubs)
    with summary_cols[4]:
        speakers = len(db_df[db_df["Speaker/Presenter"] == "✅"])
        st.metric("Conference Speakers", speakers)
    
    # Funding breakdown
    st.markdown("### 💰 Funding Stage Breakdown")
    funding_counts = db_df["Funding Stage"].value_counts().reset_index()
    funding_counts.columns = ["Funding Stage", "Count"]
    
    fig_funding = px.bar(
        funding_counts,
        x="Funding Stage",
        y="Count",
        color="Count",
        color_continuous_scale="Viridis",
        title="Leads by Funding Stage"
    )
    st.plotly_chart(fig_funding, use_container_width=True)

with main_tab1:
    # Filters in columns
    st.subheader("🔍 Search & Filter")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        query = st.text_input(
            "Keyword filter",
            value="",
            placeholder="e.g., liver, toxicology, 3D",
            help="Filter by keywords in title, company, or publications"
        )

    with col2:
        location_filter = st.text_input(
            "Location filter",
            value="",
            placeholder="e.g., Boston, Cambridge, Basel",
            help="Filter by person location or company HQ"
        )

    with col3:
        min_score = st.slider(
            "Minimum score",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            help="Only show leads with propensity score above this threshold"
        )

    with col4:
        use_live = st.toggle(
            "Include PubMed Authors",
            value=False,
            help="Fetch recent authors from PubMed who published on relevant topics"
        )

    # Action button
    run_button = st.button("🚀 Run Lead Scoring", type="primary", use_container_width=True)

    # Build workflow
    workflow = build_workflow()

    if run_button:
        with st.spinner("Running identification, enrichment, and ranking pipeline..."):
            initial_state = LeadState(
                query=query,
                location_filter=location_filter,
                min_score=min_score,
                use_live_sources=use_live,
            )
            result = workflow.invoke(initial_state.model_dump())
            leads = result.get("leads", [])

        if not leads:
            st.warning("⚠️ No leads matched the current filters. Try broadening your query, lowering the min score, or clearing the location filter.")
        else:
            df = pd.DataFrame(leads)
            
            # Dashboard metrics
            st.markdown("---")
            st.subheader("📊 Dashboard Overview")
            
            metric_cols = st.columns(5)
            
            with metric_cols[0]:
                st.metric("Total Leads", len(df))
            
            with metric_cols[1]:
                avg_score = df["propensity_score"].mean()
                st.metric("Avg Score", f"{avg_score:.1f}")
            
            with metric_cols[2]:
                high_prob = len(df[df["propensity_score"] >= 70])
                st.metric("High Probability", high_prob, help="Leads with score ≥70")
            
            with metric_cols[3]:
                with_pubs = len(df[df["recent_publications"].str.len() > 0])
                st.metric("With Publications", with_pubs)
            
            with metric_cols[4]:
                conference_speakers = df["is_conference_speaker_or_presenter"].sum()
                st.metric("Conference Speakers", int(conference_speakers))
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📋 Lead Table", "📈 Analytics", "🗺️ Location Analysis"])
            
            with tab1:
                # Prepare display dataframe
                display_cols = [
                    "propensity_score",
                    "name",
                    "title",
                    "company",
                    "person_location",
                    "company_hq",
                    "email",
                    "linkedin_url",
                    "funding_stage",
                    "uses_similar_tech",
                    "open_to_nams",
                    "recent_publications",
                    "is_conference_attendee",
                    "is_conference_speaker_or_presenter",
                ]
                
                display_df = df[[col for col in display_cols if col in df.columns]].copy()
                display_df = display_df.rename(
                    columns={
                        "propensity_score": "Score",
                        "person_location": "Person Location",
                        "company_hq": "Company HQ",
                        "linkedin_url": "LinkedIn",
                        "uses_similar_tech": "Uses 3D/In-Vitro",
                        "open_to_nams": "Open to NAMs",
                        "recent_publications": "Recent Publications",
                        "is_conference_attendee": "Conference Attendee",
                        "is_conference_speaker_or_presenter": "Speaker/Presenter",
                        "funding_stage": "Funding Stage",
                    }
                )
                
                st.caption("🎯 Higher scores = stronger role fit, budget signals, scientific intent, and market activity.")
                
                # Color the score column
                def color_score(val):
                    if val >= 70:
                        return 'background-color: #10b981; color: white'
                    elif val >= 40:
                        return 'background-color: #f59e0b; color: white'
                    else:
                        return 'background-color: #ef4444; color: white'
                
                styled_df = display_df.style.applymap(color_score, subset=['Score'])
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    height=500,
                )
                
                # Download buttons
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    csv_buffer = io.StringIO()
                    display_df.to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv_buffer.getvalue(),
                        file_name="euprime_3d_invitro_leads.csv",
                        mime="text/csv",
                    )
                with col_dl2:
                    excel_buffer = io.BytesIO()
                    display_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                    st.download_button(
                        label="📥 Download as Excel",
                        data=excel_buffer.getvalue(),
                        file_name="euprime_3d_invitro_leads.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
                    )
                
                st.info("""
                **📍 Location Split Note:**  
                This table separates **Person Location** (where they work remotely) from **Company HQ** 
                to help Business Development decide when to call vs. propose an in-person meeting.
                """)
            
            with tab2:
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    # Score distribution histogram
                    fig_hist = px.histogram(
                        df, 
                        x="propensity_score", 
                        nbins=10,
                        title="Score Distribution",
                        labels={"propensity_score": "Propensity Score", "count": "Number of Leads"},
                        color_discrete_sequence=["#667eea"]
                    )
                    fig_hist.update_layout(
                        showlegend=False,
                        xaxis_title="Propensity Score",
                        yaxis_title="Number of Leads"
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                with col_chart2:
                    # Funding stage breakdown
                    funding_counts = df["funding_stage"].value_counts().reset_index()
                    funding_counts.columns = ["Funding Stage", "Count"]
                    fig_pie = px.pie(
                        funding_counts, 
                        values="Count", 
                        names="Funding Stage",
                        title="Leads by Funding Stage",
                        color_discrete_sequence=px.colors.qualitative.Set2
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                # Score breakdown by signal
                st.subheader("🎯 Score Composition Analysis")
                
                # Calculate average characteristics for high vs low scorers
                high_scorers = df[df["propensity_score"] >= 70]
                low_scorers = df[df["propensity_score"] < 40]
                
                if len(high_scorers) > 0 and len(low_scorers) > 0:
                    comparison_data = {
                        "Metric": ["Uses 3D/In-Vitro Tech", "Open to NAMs", "Has Publications", "Conference Speaker", "Conference Attendee"],
                        "High Scorers (≥70)": [
                            f"{high_scorers['uses_similar_tech'].mean()*100:.0f}%",
                            f"{high_scorers['open_to_nams'].mean()*100:.0f}%",
                            f"{(high_scorers['recent_publications'].str.len() > 0).mean()*100:.0f}%",
                            f"{high_scorers['is_conference_speaker_or_presenter'].mean()*100:.0f}%",
                            f"{high_scorers['is_conference_attendee'].mean()*100:.0f}%",
                        ],
                        "Low Scorers (<40)": [
                            f"{low_scorers['uses_similar_tech'].mean()*100:.0f}%",
                            f"{low_scorers['open_to_nams'].mean()*100:.0f}%",
                            f"{(low_scorers['recent_publications'].str.len() > 0).mean()*100:.0f}%",
                            f"{low_scorers['is_conference_speaker_or_presenter'].mean()*100:.0f}%",
                            f"{low_scorers['is_conference_attendee'].mean()*100:.0f}%",
                        ]
                    }
                    st.table(pd.DataFrame(comparison_data))
            
            with tab3:
                st.subheader("🌍 Geographic Distribution")
                
                # Location analysis
                location_counts = df["company_hq"].value_counts().head(10).reset_index()
                location_counts.columns = ["Company HQ", "Count"]
                
                fig_bar = px.bar(
                    location_counts, 
                    x="Company HQ", 
                    y="Count",
                    title="Top 10 Company HQ Locations",
                    color="Count",
                    color_continuous_scale="Viridis"
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # Hub vs Non-Hub analysis
                hub_locations = ["Boston", "Cambridge", "Massachusetts", "Bay Area", "San Francisco", 
                               "San Diego", "Basel", "Cambridge UK", "Oxford", "London", "Golden Triangle"]
                
                def is_hub(location):
                    if pd.isna(location):
                        return False
                    return any(hub.lower() in location.lower() for hub in hub_locations)
                
                df["is_hub"] = df["company_hq"].apply(is_hub)
                hub_stats = df.groupby("is_hub")["propensity_score"].mean().reset_index()
                hub_stats["Location Type"] = hub_stats["is_hub"].map({True: "Biotech Hub", False: "Other Location"})
                
                col_hub1, col_hub2 = st.columns(2)
                
                with col_hub1:
                    hub_count = df["is_hub"].sum()
                    non_hub_count = len(df) - hub_count
                    st.metric("Leads in Biotech Hubs", f"{hub_count} ({hub_count/len(df)*100:.0f}%)")
                
                with col_hub2:
                    if len(hub_stats) == 2:
                        hub_avg = hub_stats[hub_stats["is_hub"] == True]["propensity_score"].values
                        if len(hub_avg) > 0:
                            st.metric("Avg Score (Hub Leads)", f"{hub_avg[0]:.1f}")
                
                st.caption("**Biotech Hubs:** Boston/Cambridge MA, Bay Area, San Diego, Basel, Cambridge UK, Oxford, London")

    else:
        st.info("👆 Set your filters and click **Run Lead Scoring** to see the demo.")
        
        # Show sample workflow explanation
        with st.expander("ℹ️ How the Lead Scoring Works"):
            st.markdown("""
            ### 3-Stage Pipeline
            
            **Stage 1: Identification**
            - Scan profiles from demo database + optional PubMed authors
            - Target roles: Director of Toxicology, Head of Safety, VP Preclinical, etc.
            
            **Stage 2: Enrichment**
            - Gather context: funding stage, tech signals, publications
            - Distinguish Person Location vs. Company HQ
            
            **Stage 3: Ranking (Propensity Score 0-100)**
            
            | Signal | Weight |
            |--------|--------|
            | Role Fit (Director/VP + Toxicology/Safety) | +30 |
            | Company Intent (Series A/B funding) | +20 |
            | Uses Similar Tech (3D models, organ-on-chip) | +15 |
            | Open to NAMs | +10 |
            | Located in Biotech Hub | +10 |
            | Published on DILI/Liver Toxicity | +40 |
            | Conference Speaker | +15 |
            
            **Example:**
            - Junior Scientist at unfunded startup → Score: ~15
            - Director of Safety at Series B biotech with DILI publications → Score: ~95
            """)

# Footer
st.markdown("---")
st.caption("💡 **Euprime Demo** | 3D In-Vitro Models for Researchers Designing New Therapies")
