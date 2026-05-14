"""
================================================================
  Job Application Agent — Anjuleeca Acharya
  GitHub: github.com/anjuleeca
================================================================
  WHAT THIS AGENT DOES:
    1. Searches jobs via Google Jobs / LinkedIn / Indeed
    2. Scores each job against your resume profile (0-100)
    3. Filters out low-fit roles automatically
    4. Generates a tailored cover letter using Claude
    5. Drafts a customised resume summary per job
    6. Tracks everything in a local SQLite database
    7. Presents a review dashboard — YOU approve each application

  WHAT YOU ALWAYS CONTROL:
    - Every submission requires your explicit click to proceed
    - You review the cover letter before it goes anywhere
    - The agent never submits anything automatically

  INSTALL:
    pip install anthropic requests beautifulsoup4 streamlit pandas

  RUN DASHBOARD:
    streamlit run dashboard.py

  RUN AGENT ONLY (no UI):
    python agent.py --search --keywords "Director of Analytics"
================================================================
"""

import os
import json
import time
import sqlite3
import argparse
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    import anthropic
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False
    print("⚠  pip install anthropic")

try:
    import requests
    from bs4 import BeautifulSoup
    HTTP_OK = True
except ImportError:
    HTTP_OK = False
    print("⚠  pip install requests beautifulsoup4")

# ─────────────────────────────────────────────────────────────
#  CANDIDATE PROFILE  (pulled from your resume)
# ─────────────────────────────────────────────────────────────

CANDIDATE = {
    "name":     "Anjuleeca Acharya",
    "email":    "anjuleeca@gmail.com",
    "phone":    "(510) 417-5113",
    "location": "Fremont, CA",
    "linkedin": "linkedin.com/in/anjuleeca",
    "github":   "github.com/anjuleeca",
    "title":    "Senior Data, Reporting & Analytics Leader",
    "years_exp": 16,
    "summary": (
        "MBA and B.Sc. Business Intelligence/Data Warehousing professional with 16+ years "
        "of experience delivering enterprise analytics, data warehouse solutions, AI/ML "
        "implementations, Python-based data science, and actionable insights across "
        "Technology, Education, Healthcare, Insurance, and Public Safety sectors."
    ),
    "skills": [
        "Oracle Analytics Cloud", "Power BI", "Tableau", "IBM Cognos", "OBIEE", "Peregrine",
        "Microsoft Fabric", "Python", "SQL", "PL/SQL", "T-SQL", "R",
        "SSIS", "Informatica PowerCenter", "IICS", "IBM DataStage", "Oracle Data Integrator",
        "Oracle (11g-19c)", "SQL Server", "DB2", "Snowflake", "Azure SQL", "PostgreSQL",
        "AWS", "OCI", "Databricks",
        "Oracle Machine Learning", "ARIMAX", "SARIMAX", "scikit-learn", "Jupyter Notebooks",
        "RAG pipelines", "FAISS", "AI agents", "LLM integration",
        "Azure DevOps", "Agile", "Scrum", "ArcGIS", "SharePoint",
        "Data governance", "Data architecture", "ETL", "Data warehouse",
        "BI strategy", "Executive dashboards", "KPI reporting",
    ],
    "industries": ["Public Safety", "Healthcare", "Insurance", "Technology", "Education"],
    "achievements": [
        "President Award — WCIRB California, 30% budget savings",
        "2x Above and Beyond Award — WCIRB California",
        "Built AI/ML forecasting for SFPD — briefed Chief of Police and Mayor",
        "Led BI ecosystem across 17 Kaiser Permanente medical centers",
        "IBM Cognos write-back solution presented at Northern California Cognos User Group",
        "Honored Listee — Marquis Who's Who 2023",
    ],
    "target_titles": [
        "Director of Analytics",
        "Head of Business Intelligence",
        "Senior Analytics Manager",
        "Principal Data Architect",
        "Director of Data and Analytics",
        "VP of Analytics",
        "Chief Data Officer",
        "Analytics Engineering Manager",
        "Senior BI Architect",
        "Director of Data Engineering",
    ],
    "target_salary_min": 180000,
    "target_locations": ["San Francisco, CA", "Bay Area, CA", "Remote", "Oakland, CA", "Fremont, CA"],
    "certifications": [
        "Oracle Analytics Cloud Certified",
        "IBM TM1 Certified Developer",
        "IBM Cognos Analytics for Advanced Author",
        "Microsoft Power BI Certified",
        "WCIRB Comp Essential Certified",
    ],
}


# ─────────────────────────────────────────────────────────────
#  DATA MODELS
# ─────────────────────────────────────────────────────────────

@dataclass
class JobListing:
    id:           str
    title:        str
    company:      str
    location:     str
    description:  str
    url:          str
    source:       str
    salary_min:   int = 0
    salary_max:   int = 0
    posted_date:  str = ""
    fit_score:    int = 0
    fit_reasons:  str = ""
    status:       str = "new"       # new | reviewed | approved | applied | rejected
    cover_letter: str = ""
    resume_summary: str = ""
    notes:        str = ""
    created_at:   str = ""


# ─────────────────────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────────────────────

DB_PATH = "job_applications.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT, company TEXT, location TEXT,
            description TEXT, url TEXT, source TEXT,
            salary_min INTEGER DEFAULT 0,
            salary_max INTEGER DEFAULT 0,
            posted_date TEXT,
            fit_score INTEGER DEFAULT 0,
            fit_reasons TEXT,
            status TEXT DEFAULT 'new',
            cover_letter TEXT,
            resume_summary TEXT,
            notes TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_job(job: JobListing):
    conn = sqlite3.connect(DB_PATH)
    data = asdict(job)
    cols  = ", ".join(data.keys())
    marks = ", ".join("?" for _ in data)
    vals  = list(data.values())
    conn.execute(
        f"INSERT OR REPLACE INTO jobs ({cols}) VALUES ({marks})", vals
    )
    conn.commit()
    conn.close()

def get_jobs(status=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status=? ORDER BY fit_score DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY fit_score DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_job_status(job_id: str, status: str, notes: str = ""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE jobs SET status=?, notes=? WHERE id=?",
        (status, notes, job_id)
    )
    conn.commit()
    conn.close()

def update_cover_letter(job_id: str, cover_letter: str, resume_summary: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE jobs SET cover_letter=?, resume_summary=? WHERE id=?",
        (cover_letter, resume_summary, job_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
#  JOB SEARCH  (Google Jobs via SerpAPI or direct scrape)
# ─────────────────────────────────────────────────────────────

DEMO_JOBS = [
    {
        "title": "Director of Analytics",
        "company": "Salesforce",
        "location": "San Francisco, CA (Hybrid)",
        "url": "https://salesforce.com/careers",
        "source": "demo",
        "posted_date": datetime.today().strftime("%Y-%m-%d"),
        "description": """
We are seeking a Director of Analytics to lead our enterprise data and reporting function.

Responsibilities:
- Lead a team of 10+ data analysts and BI engineers
- Define and execute analytics strategy across the organization
- Architect and govern enterprise data warehouse solutions
- Deliver executive dashboards and KPI frameworks to C-suite
- Partner with product and engineering on data infrastructure

Requirements:
- 10+ years of experience in analytics and BI
- Expert in Power BI, Tableau, or Oracle Analytics
- Strong SQL, Python, and data modeling skills
- Experience with cloud data platforms (Snowflake, Azure, AWS)
- MBA or advanced degree preferred
- Track record of leading cross-functional analytics teams
- Experience with AI/ML a strong plus

Compensation: $180,000 - $240,000 base + equity + bonus
        """.strip()
    },
    {
        "title": "Head of Business Intelligence",
        "company": "Kaiser Permanente",
        "location": "Oakland, CA (Hybrid)",
        "url": "https://kaiserpermanente.org/careers",
        "source": "demo",
        "posted_date": datetime.today().strftime("%Y-%m-%d"),
        "description": """
Kaiser Permanente seeks a Head of BI to lead analytics transformation across our healthcare network.

Responsibilities:
- Lead BI platform strategy and roadmap across 15+ medical centers
- Govern enterprise data assets — quality, security, lifecycle
- Build and mentor a team of analysts and engineers
- Drive adoption of self-service analytics tools
- Deliver operational and clinical dashboards

Requirements:
- 12+ years of analytics and BI experience
- Deep experience with IBM Cognos or Oracle Analytics
- Strong background in healthcare data (HIPAA, HEDIS, clinical metrics)
- PL/SQL, Python, ETL pipeline experience
- Experience managing cross-functional teams and stakeholders
- Familiarity with AI/ML and predictive analytics a plus

Compensation: $200,000 - $260,000 + benefits
        """.strip()
    },
    {
        "title": "Senior Analytics Engineering Manager",
        "company": "Stripe",
        "location": "San Francisco, CA / Remote",
        "url": "https://stripe.com/jobs",
        "source": "demo",
        "posted_date": datetime.today().strftime("%Y-%m-%d"),
        "description": """
Stripe is hiring a Senior Analytics Engineering Manager to own our data platform.

Responsibilities:
- Own the analytics engineering roadmap — dbt, Snowflake, Looker
- Lead a team of analytics engineers and data scientists
- Define data modeling standards and governance frameworks
- Build AI/ML-powered analytics pipelines
- Partner with Finance, Product, and Operations on data strategy

Requirements:
- 8+ years analytics/data engineering experience
- Expert SQL, Python, and modern data stack (dbt, Airflow, Snowflake)
- Experience with LLM and GenAI tooling a strong plus
- Strong communication — can present to executives
- Track record of building and scaling data teams

Compensation: $190,000 - $280,000 base + equity
        """.strip()
    },
    {
        "title": "Principal Data Architect",
        "company": "UCSF Health",
        "location": "San Francisco, CA",
        "url": "https://ucsf.edu/jobs",
        "source": "demo",
        "posted_date": datetime.today().strftime("%Y-%m-%d"),
        "description": """
UCSF Health is seeking a Principal Data Architect to lead our enterprise data strategy.

Responsibilities:
- Design and govern enterprise data architecture across clinical and operational systems
- Lead implementation of cloud data platform (Azure / Oracle Cloud)
- Build data governance frameworks and MDM policies
- Partner with clinical informatics on AI/ML data products
- Mentor a team of data engineers and architects

Requirements:
- 10+ years of data architecture and warehousing experience
- Expert in Oracle, SQL Server, Azure SQL
- Strong Python and ETL pipeline design
- Healthcare data experience (HL7, FHIR, Epic) preferred
- Oracle Analytics or Power BI expertise
- Excellent executive communication skills

Compensation: $170,000 - $220,000
        """.strip()
    },
    {
        "title": "VP of Data & Analytics",
        "company": "Levi Strauss & Co.",
        "location": "San Francisco, CA",
        "url": "https://levistrauss.com/careers",
        "source": "demo",
        "posted_date": datetime.today().strftime("%Y-%m-%d"),
        "description": """
Levi's is looking for a VP of Data & Analytics to drive our global analytics transformation.

Responsibilities:
- Define enterprise data strategy and 3-year roadmap
- Lead 30+ person data, analytics, and BI organization
- Own enterprise data platform — cloud migration, governance, quality
- Build AI/ML capabilities across marketing, supply chain, and retail

Requirements:
- MBA or equivalent
- 15+ years analytics leadership experience
- Track record of enterprise-scale BI and data platform delivery
- Strong Python, SQL, cloud platform expertise
- Excellent executive presence — board-level communication

Compensation: $250,000 - $350,000 + equity + bonus
        """.strip()
    },
]

def search_jobs_demo(keywords: str, location: str = "San Francisco, CA") -> list[JobListing]:
    """Returns demo job listings. Replace with real API call in production."""
    print(f"\n🔍 Searching for: '{keywords}' near {location}")
    print("   [Demo mode — returning synthetic job listings]")
    print("   To use real jobs: set SERPAPI_KEY env var\n")

    jobs = []
    for raw in DEMO_JOBS:
        job_id = hashlib.md5(f"{raw['company']}{raw['title']}".encode()).hexdigest()[:12]
        jobs.append(JobListing(
            id           = job_id,
            title        = raw["title"],
            company      = raw["company"],
            location     = raw["location"],
            description  = raw["description"],
            url          = raw["url"],
            source       = raw["source"],
            posted_date  = raw["posted_date"],
            created_at   = datetime.now().isoformat(),
        ))
    return jobs

def search_jobs_serpapi(keywords: str, location: str = "San Francisco, CA") -> list[JobListing]:
    """
    Search Google Jobs via SerpAPI.
    Get a free API key at: https://serpapi.com (100 searches/month free)
    Set env var: export SERPAPI_KEY=your_key
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key or not HTTP_OK:
        return search_jobs_demo(keywords, location)

    print(f"\n🔍 Searching Google Jobs: '{keywords}' in {location}")
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "engine":   "google_jobs",
                "q":        keywords,
                "location": location,
                "api_key":  api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for item in data.get("jobs_results", [])[:20]:
            job_id = hashlib.md5(f"{item.get('company_name','')}{item.get('title','')}".encode()).hexdigest()[:12]

            # Parse salary if present
            sal_min, sal_max = 0, 0
            sal_info = item.get("detected_extensions", {}).get("salary", "")
            if sal_info:
                import re
                nums = re.findall(r'\d[\d,]*', sal_info.replace(",",""))
                if len(nums) >= 2:
                    sal_min, sal_max = int(nums[0]), int(nums[1])
                elif len(nums) == 1:
                    sal_min = sal_max = int(nums[0])

            desc = item.get("description", "")
            highlights = item.get("job_highlights", [])
            for h in highlights:
                desc += "\n" + h.get("title","") + ":\n"
                desc += "\n".join(f"• {i}" for i in h.get("items",[]))

            jobs.append(JobListing(
                id          = job_id,
                title       = item.get("title", ""),
                company     = item.get("company_name", ""),
                location    = item.get("location", ""),
                description = desc,
                url         = item.get("share_link", item.get("related_links",[{}])[0].get("link","")),
                source      = "Google Jobs",
                salary_min  = sal_min,
                salary_max  = sal_max,
                posted_date = item.get("detected_extensions",{}).get("posted_at",""),
                created_at  = datetime.now().isoformat(),
            ))
        print(f"   ✓ Found {len(jobs)} jobs\n")
        return jobs
    except Exception as e:
        print(f"   ✗ SerpAPI error: {e}. Falling back to demo data.")
        return search_jobs_demo(keywords, location)


# ─────────────────────────────────────────────────────────────
#  FIT SCORING ENGINE  (Claude-powered)
# ─────────────────────────────────────────────────────────────

def score_job_fit(job: JobListing) -> tuple[int, str]:
    """
    Use Claude to score how well this job matches Anjuleeca's profile.
    Returns (score 0-100, explanation string)
    """
    if not ANTHROPIC_OK:
        return _score_keyword_fallback(job)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("   ⚠  ANTHROPIC_API_KEY not set — using keyword scoring")
        return _score_keyword_fallback(job)

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are a senior recruiter evaluating job fit for a candidate.

CANDIDATE PROFILE:
- Name: {CANDIDATE['name']}
- Title: {CANDIDATE['title']}
- Experience: {CANDIDATE['years_exp']} years
- Key skills: {', '.join(CANDIDATE['skills'][:20])}
- Industries: {', '.join(CANDIDATE['industries'])}
- Target roles: {', '.join(CANDIDATE['target_titles'][:5])}
- Target salary: ${CANDIDATE['target_salary_min']:,}+
- Notable achievements: {'; '.join(CANDIDATE['achievements'][:3])}

JOB LISTING:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Salary: ${job.salary_min:,} - ${job.salary_max:,} (if listed)

Description:
{job.description[:2000]}

Evaluate this job's fit for the candidate. Respond ONLY with valid JSON:
{{
  "score": <integer 0-100>,
  "match_reasons": ["reason1", "reason2", "reason3"],
  "gap_reasons": ["gap1", "gap2"],
  "salary_fit": true/false,
  "location_fit": true/false,
  "recommendation": "apply" | "skip" | "review"
}}

Scoring guide:
90-100: Perfect fit — title, skills, salary, industry all match
75-89: Strong fit — most criteria match, minor gaps
60-74: Good fit — worth applying despite some gaps
40-59: Partial fit — significant gaps but transferable skills exist
0-39: Poor fit — skip this role"""

    try:
        resp = client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 500,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data   = json.loads(raw.strip())
        score  = int(data.get("score", 50))
        reasons = data.get("match_reasons", []) + [f"⚠ {g}" for g in data.get("gap_reasons", [])]
        return score, " | ".join(reasons)
    except Exception as e:
        print(f"   ⚠  Claude scoring failed ({e}), using keyword fallback")
        return _score_keyword_fallback(job)

def _score_keyword_fallback(job: JobListing) -> tuple[int, str]:
    """Keyword-based scoring when Claude API is unavailable."""
    desc_full = (job.title + " " + job.description).lower()
    score = 40  # Base score — assume some fit
    hits  = []

    # Title match is the strongest signal
    title_matched = False
    for target in CANDIDATE["target_titles"]:
        if any(word in job.title.lower() for word in target.lower().split()):
            score += 25
            title_matched = True
            hits.append(f"Title: {job.title}")
            break
    if not title_matched and any(w in job.title.lower() for w in ["director","head","vp","principal","senior","lead"]):
        score += 10

    # Skill keyword matches
    skill_hits = 0
    for skill in CANDIDATE["skills"]:
        if skill.lower() in desc_full and skill_hits < 10:
            score += 2
            skill_hits += 1
            hits.append(skill)

    # Industry match
    for ind in CANDIDATE["industries"]:
        if ind.lower() in desc_full:
            score += 5
            hits.append(f"Industry: {ind}")
            break

    # Salary fit
    if job.salary_min >= CANDIDATE["target_salary_min"]:
        score += 8
        hits.append("Salary matches")
    elif job.salary_min == 0:
        score += 4  # Unknown salary — don't penalise

    # Location fit
    for loc in CANDIDATE["target_locations"]:
        if any(word in job.location.lower() for word in loc.lower().split(",")):
            score += 5
            break

    score = max(0, min(score, 100))
    return score, f"Keyword matches: {', '.join(hits[:5])}"


# ─────────────────────────────────────────────────────────────
#  COVER LETTER GENERATOR  (Claude-powered)
# ─────────────────────────────────────────────────────────────

def generate_cover_letter(job: JobListing) -> tuple[str, str]:
    """
    Generate a tailored cover letter and resume summary for this specific job.
    Returns (cover_letter, resume_summary)
    """
    if not ANTHROPIC_OK:
        return _cover_letter_fallback(job), ""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _cover_letter_fallback(job), ""

    client = anthropic.Anthropic(api_key=api_key)
    print(f"   ✍  Generating cover letter for {job.title} at {job.company}...")

    prompt = f"""You are a professional career writer. Generate a tailored, compelling cover letter for this candidate and job.

CANDIDATE:
Name: {CANDIDATE['name']}
Email: {CANDIDATE['email']}
Phone: {CANDIDATE['phone']}
LinkedIn: {CANDIDATE['linkedin']}
Experience: {CANDIDATE['years_exp']} years
Summary: {CANDIDATE['summary']}
Key achievements:
{chr(10).join(f'• {a}' for a in CANDIDATE['achievements'])}
Skills: {', '.join(CANDIDATE['skills'][:15])}
Certifications: {', '.join(CANDIDATE['certifications'])}

TARGET JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description[:2000]}

Write TWO things:

1. COVER_LETTER: A 3-paragraph professional cover letter. 
   - Para 1: Hook — why THIS role at THIS company excites her specifically
   - Para 2: Her most relevant 2-3 achievements that directly map to the job requirements
   - Para 3: Forward-looking close — what she will bring to the team
   - Tone: Confident, specific, data-driven. No fluff.
   - Length: 250-300 words max

2. RESUME_SUMMARY: A 3-sentence tailored summary for the top of her resume for THIS specific role.
   Focus on the keywords and priorities in this job description.

Format your response EXACTLY like this (include the markers):
---COVER_LETTER---
[cover letter text]
---RESUME_SUMMARY---
[resume summary text]"""

    try:
        resp = client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 1200,
            messages   = [{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text
        parts = text.split("---RESUME_SUMMARY---")
        cl_part  = parts[0].replace("---COVER_LETTER---", "").strip()
        rs_part  = parts[1].strip() if len(parts) > 1 else ""
        return cl_part, rs_part
    except Exception as e:
        print(f"   ⚠  Cover letter generation failed: {e}")
        return _cover_letter_fallback(job), ""

def _cover_letter_fallback(job: JobListing) -> str:
    return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job.title} position at {job.company}. With over 16 years of enterprise analytics leadership experience across Public Safety, Healthcare, and Insurance sectors, I am confident I can bring immediate and lasting value to your team.

Throughout my career, I have led end-to-end BI and analytics transformations — most recently at the San Francisco Police Department, where I built AI/ML forecasting systems briefed to the Chief of Police and Mayor of San Francisco, and previously at WCIRB California, where I received the President Award for delivering a new analytics product 30% under budget. I bring deep expertise in Power BI, Oracle Analytics Cloud, IBM Cognos, Python, and Microsoft Fabric, combined with the strategic leadership skills to define roadmaps and govern enterprise data programs.

I would welcome the opportunity to discuss how my background in building data-driven organizations can support {job.company}'s goals. Thank you for your consideration.

Sincerely,
{CANDIDATE['name']}
{CANDIDATE['phone']} | {CANDIDATE['email']}
{CANDIDATE['linkedin']}"""


# ─────────────────────────────────────────────────────────────
#  MAIN AGENT LOOP
# ─────────────────────────────────────────────────────────────

class JobApplicationAgent:
    def __init__(self):
        init_db()
        print("✅ Job Application Agent initialized")
        print(f"   Candidate: {CANDIDATE['name']}")
        print(f"   Target titles: {', '.join(CANDIDATE['target_titles'][:3])}...")
        print(f"   Database: {DB_PATH}\n")

    def run_search(self, keywords: str = None, location: str = "San Francisco Bay Area, CA"):
        """Search for jobs, score them, and save to DB."""
        if not keywords:
            keywords = "Director of Analytics OR Head of Business Intelligence OR Senior Analytics Manager"

        jobs = search_jobs_serpapi(keywords, location)
        print(f"Found {len(jobs)} listings. Scoring fit...\n")

        scored = 0
        skipped = 0
        for job in jobs:
            print(f"  ⚡ {job.title} @ {job.company}")
            score, reasons = score_job_fit(job)
            job.fit_score   = score
            job.fit_reasons = reasons

            if score >= 60:
                # Generate cover letter for good fits
                cl, rs = generate_cover_letter(job)
                job.cover_letter    = cl
                job.resume_summary  = rs
                job.status = "reviewed"
                save_job(job)
                scored += 1
                print(f"     ✓ Score: {score}/100 — saved for review")
            else:
                job.status = "rejected"
                save_job(job)
                skipped += 1
                print(f"     ✗ Score: {score}/100 — skipped (low fit)")

            time.sleep(0.5)  # be nice to APIs

        print(f"\n{'='*50}")
        print(f"  Search complete: {scored} jobs ready for review, {skipped} skipped")
        print(f"  Run: streamlit run dashboard.py  to review and approve")
        print(f"{'='*50}\n")
        return scored

    def generate_materials_for_job(self, job_id: str):
        """Regenerate cover letter + resume summary for a specific job."""
        jobs = get_jobs()
        job_data = next((j for j in jobs if j["id"] == job_id), None)
        if not job_data:
            print(f"Job {job_id} not found")
            return

        job = JobListing(**job_data)
        cl, rs = generate_cover_letter(job)
        update_cover_letter(job_id, cl, rs)
        print(f"✓ Cover letter updated for {job.title} @ {job.company}")

    def get_stats(self):
        """Print application pipeline stats."""
        all_jobs = get_jobs()
        by_status = {}
        for j in all_jobs:
            s = j["status"]
            by_status[s] = by_status.get(s, 0) + 1

        print("\n📊 Application Pipeline Stats")
        print("─" * 35)
        for status, count in sorted(by_status.items()):
            bar = "█" * count
            print(f"  {status:<12} {bar} {count}")
        print(f"\n  Total: {len(all_jobs)} jobs tracked")
        print(f"  DB: {DB_PATH}\n")


# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Job Application Agent — Anjuleeca Acharya")
    parser.add_argument("--search",   action="store_true", help="Search for new jobs")
    parser.add_argument("--keywords", type=str, default=None, help="Search keywords")
    parser.add_argument("--location", type=str, default="San Francisco Bay Area, CA")
    parser.add_argument("--stats",    action="store_true", help="Show pipeline stats")
    args = parser.parse_args()

    agent = JobApplicationAgent()

    if args.search:
        agent.run_search(keywords=args.keywords, location=args.location)
    if args.stats:
        agent.get_stats()
    if not args.search and not args.stats:
        print("Usage:")
        print("  python agent.py --search")
        print("  python agent.py --search --keywords 'VP of Analytics'")
        print("  python agent.py --stats")
        print("  streamlit run dashboard.py  (review and approve applications)\n")


if __name__ == "__main__":
    main()
