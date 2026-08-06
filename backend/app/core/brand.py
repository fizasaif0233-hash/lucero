"""Brand + knowledge architecture for L.U.C.E.R.O Phase 1."""

# Primary consumer-facing brand site (future chat widget host)
PRIMARY_WEBSITE = "https://www.anthonywarrenmckinzy.com"

# Business / exchange knowledge site (RAG source, not the app shell)
KNOWLEDGE_WEBSITE = "https://www.759inc.blue"

# Seed crawl targets (same-origin paths discovered from these roots)
DEFAULT_CRAWL_SEEDS = [
    "https://www.anthonywarrenmckinzy.com",
    "https://www.759inc.blue",
]

BRAND_CONTEXT = """
## Business context (Anthony Warren McKinzy / 759 Entertainment)

Primary public brand site: https://www.anthonywarrenmckinzy.com
- Premium lifestyle / Phoenix Rising brand presence
- 759 Token ecosystem messaging, roadmap, community

Business knowledge / private exchange site: https://www.759inc.blue
- 759 Private Exchange workspace (multi-token wallet, transfers, drawings, tiers)
- Ecosystem tokens (e.g. 759, Cristalino, Añejo, Raffle, Susu)
- Operational product information for members and admins

Core businesses L.U.C.E.R.O supports:
- Blue Prince21 McKinzy / 759 Tequila (premium, additive-free direction)
- 759 Token / private exchange
- Related hospitality, distribution, marketing, and community operations

L.U.C.E.R.O (Lucero) is a SEPARATE secure dashboard for Anthony (Owner) and his wife.
A public chat widget on anthonywarrenmckinzy.com may be added later via a
JavaScript embed that calls the same FastAPI backend — no architecture rewrite.
""".strip()
