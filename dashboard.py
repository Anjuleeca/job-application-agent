"""
================================================================
  Job Application Dashboard — Anjuleeca Acharya
  Run: streamlit run dashboard.py
================================================================
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from agent import (
    JobApplicationAgent, get_jobs, update_job_status,
    update_cover_letter, generate_cover_letter, CANDIDATE,
    JobListing, DB_PATH
)

try:
    import streamlit as st
    import pandas as pd
except ImportError:
    print("Run: pip install streamlit pandas")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title  = "Job Agent — Anjuleeca Acharya",
    page_icon   = "🎯",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

st.markdown("""
<style>
    .score-high   { color: #1D9E75; font-weight: 600; font-size: 1.2rem; }
    .score-med    { color: #BA7517; font-weight: 600; font-size: 1.2rem; }
    .score-low    { color: #D85A30; font-weight: 600; font-size: 1.2rem; }
    .status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
    .stButton > button { width: 100%; }
    .job-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 8px 0; }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎯 Job Application Agent")
    st.markdown(f"**{CANDIDATE['name']}**")
    st.markdown(f"📍 {CANDIDATE['location']}")
    st.markdown(f"🔗 [{CANDIDATE['linkedin']}](https://{CANDIDATE['linkedin']})")
    st.markdown("---")

    st.markdown("**🔍 Run Job Search**")
    keywords = st.text_input(
        "Keywords",
        value="Director of Analytics OR Head of Business Intelligence",
        help="Enter job titles or keywords to search"
    )
    location = st.text_input("Location", value="San Francisco Bay Area, CA")
    min_score = st.slider("Min fit score to show", 0, 100, 60)

    if st.button("🚀 Search & Score Jobs", use_container_width=True):
        with st.spinner("Searching and scoring jobs with AI..."):
            agent = JobApplicationAgent()
            count = agent.run_search(keywords=keywords, location=location)
            st.success(f"Found {count} matching jobs! Refresh page to see results.")

    st.markdown("---")
    st.markdown("**📊 Quick Stats**")
    all_jobs = get_jobs()
    stats = {}
    for j in all_jobs:
        stats[j["status"]] = stats.get(j["status"], 0) + 1

    col1, col2 = st.columns(2)
    col1.metric("Total tracked", len(all_jobs))
    col2.metric("Ready to review", stats.get("reviewed", 0))

    st.markdown("---")
    st.markdown("**💡 Quick tips**")
    st.markdown("""
- ✅ Green score = 75+ fit
- 🟡 Yellow score = 60–74 fit
- Review cover letter before approving
- Click **Approve** to mark ready to apply
- You always control the final submit
    """)


# ─────────────────────────────────────────────────────────────
#  MAIN CONTENT
# ─────────────────────────────────────────────────────────────

st.title("🎯 Job Application Pipeline")

tabs = st.tabs(["📋 Review Queue", "✅ Approved", "📬 Applied", "📊 Analytics", "⚙️ Settings"])


# ── TAB 1: REVIEW QUEUE ───────────────────────────────────────
with tabs[0]:
    st.markdown("### Jobs ready for your review")
    st.caption("Review the AI-generated cover letter, adjust if needed, then Approve to move to your apply queue.")

    reviewed_jobs = [j for j in get_jobs() if j["status"] == "reviewed" and j["fit_score"] >= min_score]

    if not reviewed_jobs:
        st.info("No jobs in review queue. Run a search from the sidebar to find new opportunities.")
    else:
        st.markdown(f"**{len(reviewed_jobs)} jobs waiting** — sorted by fit score")

        for job in reviewed_jobs:
            score = job["fit_score"]
            score_class = "score-high" if score >= 75 else "score-med" if score >= 60 else "score-low"

            with st.expander(
                f"{'🟢' if score >= 75 else '🟡'} **{job['title']}** at {job['company']} — {job['location']}",
                expanded=False
            ):
                col1, col2, col3 = st.columns([1, 1, 1])
                col1.markdown(f"**Fit score**")
                col1.markdown(f"<span class='{score_class}'>{score}/100</span>", unsafe_allow_html=True)

                col2.markdown("**Salary**")
                if job["salary_min"] > 0:
                    col2.markdown(f"${job['salary_min']:,} – ${job['salary_max']:,}")
                else:
                    col2.markdown("Not listed")

                col3.markdown("**Source**")
                col3.markdown(f"[{job['source']}]({job['url']})")

                if job["fit_reasons"]:
                    st.markdown("**Why this fits:**")
                    for reason in job["fit_reasons"].split(" | ")[:4]:
                        if reason.strip():
                            icon = "⚠️" if reason.startswith("⚠") else "✅"
                            st.markdown(f"{icon} {reason.replace('⚠ ','')}")

                st.markdown("---")
                st.markdown("**📝 Cover Letter** *(edit before approving)*")

                cl_key = f"cl_{job['id']}"
                edited_cl = st.text_area(
                    "Cover letter",
                    value=job.get("cover_letter", ""),
                    height=280,
                    key=cl_key,
                    label_visibility="collapsed",
                )

                if job.get("resume_summary"):
                    st.markdown("**📄 Resume Summary** *(tailored for this role)*")
                    rs_key = f"rs_{job['id']}"
                    edited_rs = st.text_area(
                        "Resume summary",
                        value=job.get("resume_summary", ""),
                        height=100,
                        key=rs_key,
                        label_visibility="collapsed",
                    )
                else:
                    edited_rs = ""

                st.markdown("**📋 Job Description**")
                with st.expander("View full description"):
                    st.text(job["description"])

                st.markdown("---")
                btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

                with btn_col1:
                    if st.button("✅ Approve to apply", key=f"approve_{job['id']}", type="primary"):
                        update_cover_letter(job["id"], edited_cl, edited_rs)
                        update_job_status(job["id"], "approved", "Approved via dashboard")
                        st.success("✅ Moved to Approved queue!")
                        st.rerun()

                with btn_col2:
                    if st.button("🔄 Regen cover letter", key=f"regen_{job['id']}"):
                        with st.spinner("Generating with Claude..."):
                            j_obj = JobListing(**{k: job[k] for k in JobListing.__dataclass_fields__})
                            new_cl, new_rs = generate_cover_letter(j_obj)
                            update_cover_letter(job["id"], new_cl, new_rs)
                        st.success("Cover letter regenerated!")
                        st.rerun()

                with btn_col3:
                    if st.button("🔗 View job posting", key=f"view_{job['id']}"):
                        st.markdown(f"[Open job posting →]({job['url']})")

                with btn_col4:
                    if st.button("❌ Skip this job", key=f"skip_{job['id']}"):
                        update_job_status(job["id"], "rejected", "Skipped by user")
                        st.rerun()


# ── TAB 2: APPROVED ───────────────────────────────────────────
with tabs[1]:
    st.markdown("### Approved — ready to apply")
    st.caption("These jobs are approved. Click 'Mark as Applied' after you submit each application manually.")

    approved_jobs = [j for j in get_jobs() if j["status"] == "approved"]

    if not approved_jobs:
        st.info("No approved jobs yet. Approve jobs from the Review Queue tab.")
    else:
        for job in approved_jobs:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{job['title']}** at **{job['company']}**")
                st.caption(f"{job['location']} | Score: {job['fit_score']}/100")
            with col2:
                if st.button("📋 Copy cover letter", key=f"copy_{job['id']}"):
                    st.code(job.get("cover_letter",""), language=None)
            with col3:
                if st.button("✔️ Mark as Applied", key=f"applied_{job['id']}", type="primary"):
                    update_job_status(job["id"], "applied", f"Applied on {pd.Timestamp.now().strftime('%Y-%m-%d')}")
                    st.success(f"Marked as applied!")
                    st.rerun()

            with st.expander("View cover letter"):
                st.text(job.get("cover_letter",""))

            st.markdown("---")


# ── TAB 3: APPLIED ────────────────────────────────────────────
with tabs[2]:
    st.markdown("### Application tracker")

    applied_jobs = [j for j in get_jobs() if j["status"] == "applied"]

    if not applied_jobs:
        st.info("No applications submitted yet.")
    else:
        df = pd.DataFrame(applied_jobs)[["title","company","location","fit_score","notes","url"]]
        df.columns = ["Role", "Company", "Location", "Fit %", "Applied On", "Link"]
        st.dataframe(df, use_container_width=True)
        st.markdown(f"**{len(applied_jobs)} applications submitted**")


# ── TAB 4: ANALYTICS ──────────────────────────────────────────
with tabs[3]:
    st.markdown("### Pipeline analytics")

    all_jobs = get_jobs()
    if not all_jobs:
        st.info("No data yet. Run a search first.")
    else:
        df = pd.DataFrame(all_jobs)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total found",   len(df))
        m2.metric("High fit (75+)", len(df[df["fit_score"] >= 75]))
        m3.metric("Approved",      len(df[df["status"] == "approved"]))
        m4.metric("Applied",       len(df[df["status"] == "applied"]))

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Score distribution**")
            bins = {"90-100": 0, "75-89": 0, "60-74": 0, "40-59": 0, "0-39": 0}
            for _, row in df.iterrows():
                s = row["fit_score"]
                if s >= 90:   bins["90-100"] += 1
                elif s >= 75: bins["75-89"] += 1
                elif s >= 60: bins["60-74"] += 1
                elif s >= 40: bins["40-59"] += 1
                else:         bins["0-39"] += 1
            st.bar_chart(bins)

        with col2:
            st.markdown("**Status breakdown**")
            status_counts = df["status"].value_counts().to_dict()
            st.bar_chart(status_counts)

        st.markdown("**All tracked jobs**")
        display_df = df[["title","company","location","fit_score","status"]].copy()
        display_df.columns = ["Role","Company","Location","Fit Score","Status"]
        st.dataframe(
            display_df.sort_values("Fit Score", ascending=False),
            use_container_width=True
        )


# ── TAB 5: SETTINGS ───────────────────────────────────────────
with tabs[4]:
    st.markdown("### Agent settings")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**API keys**")
        st.text_input("ANTHROPIC_API_KEY", type="password", value=os.getenv("ANTHROPIC_API_KEY",""),
                      help="For cover letter generation and AI scoring. Get at console.anthropic.com")
        st.text_input("SERPAPI_KEY", type="password", value=os.getenv("SERPAPI_KEY",""),
                      help="For real Google Jobs search. Free tier: 100 searches/month. serpapi.com")
        st.caption("Set these as environment variables: export ANTHROPIC_API_KEY=sk-...")

    with col2:
        st.markdown("**Target preferences**")
        st.multiselect("Target job titles", CANDIDATE["target_titles"], default=CANDIDATE["target_titles"][:5])
        st.slider("Minimum salary ($K)", 100, 400, CANDIDATE["target_salary_min"]//1000)
        st.multiselect("Target locations", CANDIDATE["target_locations"], default=CANDIDATE["target_locations"])

    st.markdown("---")
    st.markdown("**Database**")
    st.caption(f"Data stored at: `{DB_PATH}`")
    if st.button("🗑️ Clear all job data", type="secondary"):
        st.warning("This will delete all tracked jobs. This action cannot be undone.")
        if st.button("Confirm delete", type="secondary"):
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM jobs")
            conn.commit()
            conn.close()
            st.success("Database cleared.")
            st.rerun()
