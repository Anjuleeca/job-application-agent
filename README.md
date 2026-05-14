# job-application-agent
# 🤖 Crime Analytics AI Agent
### End-to-end autonomous analytics agent for public safety intelligence
**Built by:** [Anjuleeca Acharya](https://linkedin.com/in/anjuleeca) | [github.com/anjuleeca](https://github.com/anjuleeca)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Microsoft Fabric](https://img.shields.io/badge/Microsoft_Fabric-Ready-0078D4?style=flat&logo=microsoft)](https://microsoft.com/fabric)
[![Claude API](https://img.shields.io/badge/Claude-Sonnet_4-D97757?style=flat)](https://anthropic.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat)](LICENSE)

---

## What this agent does

This project demonstrates a production-grade AI agent built on real public safety data from the San Francisco Police Department. The agent autonomously searches crime data, runs forecasting models, detects anomalies, and delivers executive-quality natural language briefings — the same class of work I built at SFPD for the Police Chief and Mayor of San Francisco.

```
Ask:   "What were the top crime trends in Mission District
        last week, and what does the forecast show for next month?"

Agent: Searches RAG memory → runs SQL query → calls ARIMAX forecasting
       → synthesises results → delivers executive briefing

Time:  < 5 seconds. No dashboard clicks. No analyst needed.
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Natural Language Interface                │
│              (Streamlit chat / REST API endpoint)            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    AI Agent Brain                            │
│              Claude Sonnet (Plan → Act → Observe loop)       │
│         Decides which tools to call and in what order        │
└──────┬──────────────┬────────────────┬───────────────┬──────┘
       │              │                │               │
  ┌────▼────┐   ┌─────▼─────┐  ┌──────▼──────┐ ┌─────▼─────┐
  │   RAG   │   │    SQL    │  │  Forecasting │ │  Alerting │
  │  Memory │   │  Query    │  │    Engine    │ │   Tool    │
  │  Tool   │   │   Tool    │  │    Tool      │ │           │
  └────┬────┘   └─────┬─────┘  └──────┬───────┘ └─────┬─────┘
       │              │                │               │
┌──────▼──────────────▼────────────────▼───────────────▼──────┐
│                    Microsoft Fabric                          │
│     OneLake · Lakehouse · Data Warehouse · ML Notebooks      │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              SFPD Open Data  (data.sfgov.org)                │
│   Incidents · Districts · Categories · Time Series           │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent tools

| Tool | What it does | Skills used |
|---|---|---|
| `query_crime_data` | RAG retrieval over crime records — semantic search using embeddings | Python, FAISS, sentence-transformers |
| `run_sql` | Executes SQL against the Fabric data warehouse for exact counts and aggregations | PL/SQL, Python, Snowflake/Oracle |
| `forecast_incidents` | Calls ARIMAX/SARIMAX time series models to predict future crime volumes | Python, statsmodels, Oracle ML |
| `detect_anomalies` | Flags statistical outliers in crime trends — proactive, no prompt needed | Python, pandas, Z-score analysis |
| `send_alert` | Pushes anomaly notifications to Slack or email | Python, REST APIs |

---

## Real-world background

This project is a direct extension of production work I delivered at the **San Francisco Police Department** (2023–present):

- Built enterprise BI solutions for Use of Force, Firearm, STOP, Incident, HRMS, Homicide, Theft, Robbery, and Vehicle Pursuit data using Oracle Analytics Cloud, Power BI, and Peregrine
- Developed ARIMAX and SARIMAX time-series forecasting models in Python, comparing outputs against Oracle Machine Learning results and actual incident data
- Used ArcGIS for geospatial crime mapping and location-based trend analysis
- Delivered dashboards and briefings to the Commander, Chief of Police, and Mayor of San Francisco
- Trained officers and commanders at the SFPD Academy to adopt data-driven decision tools

This repository modernises that work with a natural language interface, autonomous multi-tool reasoning, and Microsoft Fabric as the data platform.

---

## Quick start

### 1. Clone the repository
```bash
git clone https://github.com/anjuleeca/crime-analytics-agent.git
cd crime-analytics-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set environment variables
```bash
# Required for AI reasoning and cover letter generation
export ANTHROPIC_API_KEY=your_key_here

# Optional — for real SFPD data (otherwise uses synthetic demo data)
# Data is public at: https://data.sfgov.org
```

### 4. Build the search index
```bash
python agent.py --build-index
```

### 5. Run the chat interface
```bash
streamlit run dashboard.py
```

Your browser opens at `localhost:8501`. Start asking questions.

---

## Example queries

```
"What are the top 5 crime categories in the Tenderloin this month?"

"Compare assault rates across all districts year over year."

"Which neighborhoods have seen the biggest increase in vehicle theft?"

"Forecast homicide incidents for Mission District over the next 4 weeks."

"Are there any unusual crime spikes I should flag for the Commander?"
```

---

## Project structure

```
crime-analytics-agent/
│
├── agent.py              # Core agent — Plan/Act/Observe loop, tool definitions
├── dashboard.py          # Streamlit chat interface
├── rag_pipeline.py       # RAG memory — embeddings, FAISS index, retrieval
├── tools/
│   ├── sql_tool.py       # SQL query execution against Fabric data warehouse
│   ├── forecast_tool.py  # ARIMAX/SARIMAX forecasting wrapper
│   ├── anomaly_tool.py   # Statistical anomaly detection
│   └── alert_tool.py     # Slack/email notification dispatcher
├── data/
│   └── loader.py         # SFPD open data ingestion (API + CSV support)
├── requirements.txt
└── README.md
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Agent orchestration | Anthropic Claude Sonnet 4 (tool_use API) |
| Data platform | Microsoft Fabric — OneLake, Lakehouse, SQL endpoint |
| Semantic search | sentence-transformers (all-MiniLM-L6-v2) + FAISS |
| Forecasting | Python statsmodels — ARIMAX, SARIMAX |
| ML cross-validation | Oracle Machine Learning (OML) |
| Dashboards | Streamlit + Power BI Direct Lake |
| Geospatial | ArcGIS / GIS integration |
| Data source | SFPD Open Data API (data.sfgov.org) |
| Orchestration | Apache Airflow (Fabric Data Factory in production) |

---

## Microsoft Fabric integration

This project is designed to run locally for development and migrate to Microsoft Fabric for production. Three lines change between environments:

**Local (development):**
```python
# Load data from SFPD open data API
df = load_crime_data(source="api", limit=5000)

# FAISS vector store on local disk
store = VectorStore.load("crime_index")
```

**Microsoft Fabric (production):**
```python
# Load from Fabric Lakehouse via Spark
df = spark.sql("SELECT * FROM crime_lakehouse.incidents").toPandas()

# Azure AI Search replaces FAISS
from azure.search.documents import SearchClient
```

---

## Certifications & background

| Credential | Issuer |
|---|---|
| Oracle Analytics Cloud Certified | Oracle |
| Microsoft Power BI Certified | Microsoft |
| IBM Cognos Analytics for Advanced Author | IBM |
| IBM TM1 Certified Developer | IBM |
| WCIRB Comp Essential Certified | WCIRB |

**16+ years of enterprise analytics** across Public Safety · Healthcare · Insurance · Technology

**Industries:** San Francisco Police Department · Kaiser Permanente · WCIRB California · Intel · UC Office of the President

---

## Related projects

| Project | Description |
|---|---|
| [📊 Fabric + Power BI Direct Lake Dashboard](../fabric-powerbi-dashboard) | Enterprise crime dashboard with Copilot Q&A |
| [🔍 WCIRB Class Intel — Case Study](../wcirb-class-intel) | President Award-winning insurance analytics product |
| [🏥 Kaiser Permanente BI Ecosystem](../kaiser-bi-ecosystem) | 17-medical-center BI architecture case study |

---

## Author

**Anjuleeca Acharya** — Senior Data, Reporting & Analytics Leader

📍 Fremont, CA (San Francisco Bay Area)
📧 anjuleeca@gmail.com
🔗 [linkedin.com/in/anjuleeca](https://linkedin.com/in/anjuleeca)
🐙 [github.com/anjuleeca](https://github.com/anjuleeca)

> *"The best data science work is invisible to the end user. They don't see the Python models or the pipelines. They just see clarity where there was confusion before."*

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <img src="https://img.shields.io/badge/Built_with-Python_%7C_Claude_%7C_Microsoft_Fabric-7F77DD?style=flat" />
  <img src="https://img.shields.io/badge/Data-SFPD_Open_Data-1D9E75?style=flat" />
  <img src="https://img.shields.io/badge/Domain-Public_Safety_Analytics-D85A30?style=flat" />
</p>


