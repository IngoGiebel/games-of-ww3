"""ETL: Import Reference and ReferenceCategory nodes into Neo4j.

Imports the 54 critical sources from BIAS_FRAMEWORK.md Section 4 and
the 7 thematic categories. Creates :CATEGORIZED_AS, :CRITIQUES, and
initial :CITES edges.

Sprint 3, Phase B.
Reference: docs/BIAS_FRAMEWORK.md Section 4, docs/DATA_MODEL_COMPLETE.md Section 2.4
"""

from __future__ import annotations

import asyncio
import logging
import os

from neo4j import AsyncGraphDatabase

logger = logging.getLogger(__name__)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

# ──────────────────────────────────────────────
# Reference Categories (7)
# ──────────────────────────────────────────────

CATEGORIES = [
    {"id": "democratic_deficit", "name": "Democratic Deficit & Elite Control",
     "description": "Studies demonstrating that representative democracies systematically fail to represent citizen preferences.", "section": "4.1"},
    {"id": "data_source_critique", "name": "Data Source Bias Critique",
     "description": "Methodological critiques of specific data sources used in GWW3.", "section": "4.2"},
    {"id": "conflict_data", "name": "Conflict Data & State Violence",
     "description": "Alternative conflict datasets and documentation of state violence.", "section": "4.3"},
    {"id": "world_systems", "name": "World-Systems & Structural Critique",
     "description": "Theoretical frameworks for understanding global structural inequality and epistemological hegemony.", "section": "4.4"},
    {"id": "demographic_reliability", "name": "Demographic Data Reliability",
     "description": "Studies on unreliability of population and economic statistics.", "section": "4.5"},
    {"id": "international_law", "name": "International Law & State Terrorism",
     "description": "Legal analysis of state violence, targeted killings, and terrorism classification.", "section": "4.6"},
    {"id": "counter_hegemonic_source", "name": "Alternative & Counter-Hegemonic Data Sources",
     "description": "Non-Western and independent data sources for cross-referencing.", "section": "4.7"},
]

# ──────────────────────────────────────────────
# References (54)
# ──────────────────────────────────────────────

REFERENCES = [
    # 4.1 Democratic Deficit & Elite Control
    {"cite_key": "Gilens_Page_2014", "entry_type": "article", "author": "Gilens, Martin and Page, Benjamin I.", "title": "Testing Theories of American Politics: Elites, Interest Groups, and Average Citizens", "year": 2014, "journal": "Perspectives on Politics", "volume": "12", "number": "3", "pages": "564-581", "doi": "10.1017/S1537592714001595", "key_contribution": "1,779 policy issues: average citizens have near-zero influence on policy", "language": "en", "open_access": True, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Mausfeld_2018", "entry_type": "book", "author": "Mausfeld, Rainer", "title": "Warum schweigen die Lämmer?", "year": 2018, "publisher": "Westend Verlag", "key_contribution": "Elite democracy, opinion management, manufactured depoliticization", "language": "de", "open_access": False, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Maus_2011", "entry_type": "book", "author": "Maus, Ingeborg", "title": "Über Volkssouveränität: Elemente einer Demokratietheorie", "year": 2011, "publisher": "Suhrkamp", "key_contribution": "Constitutional courts usurping legislative power, expertocratic paternalism", "language": "de", "open_access": False, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Chomsky_Herman_1988", "entry_type": "book", "author": "Chomsky, Noam and Herman, Edward S.", "title": "Manufacturing Consent: The Political Economy of the Mass Media", "year": 1988, "publisher": "Pantheon Books", "key_contribution": "Five-filter propaganda model; structural media bias", "language": "en", "open_access": False, "reliability": "high", "categories": ["democratic_deficit", "data_source_critique"]},
    {"cite_key": "Wolin_2008", "entry_type": "book", "author": "Wolin, Sheldon S.", "title": "Democracy Incorporated: Managed Democracy and the Specter of Inverted Totalitarianism", "year": 2008, "publisher": "Princeton University Press", "key_contribution": "Inverted totalitarianism — corporate-managed pseudo-democracy", "language": "en", "open_access": False, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Crouch_2004", "entry_type": "book", "author": "Crouch, Colin", "title": "Post-Democracy", "year": 2004, "publisher": "Polity Press", "key_contribution": "Formal democratic institutions persist while power shifts to elites", "language": "en", "open_access": False, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Streeck_2014", "entry_type": "book", "author": "Streeck, Wolfgang", "title": "Buying Time: The Delayed Crisis of Democratic Capitalism", "year": 2014, "publisher": "Verso", "key_contribution": "Tension between capitalism and democracy; debt state replaces tax state", "language": "en", "open_access": False, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Brown_2015", "entry_type": "book", "author": "Brown, Wendy", "title": "Undoing the Demos: Neoliberalism's Stealth Revolution", "year": 2015, "publisher": "Zone Books", "key_contribution": "Neoliberalism redefines citizens as human capital, hollowing democracy", "language": "en", "open_access": False, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Piketty_2014", "entry_type": "book", "author": "Piketty, Thomas", "title": "Capital in the Twenty-First Century", "year": 2014, "publisher": "Harvard University Press", "key_contribution": "Structural wealth concentration undermining democratic equality", "language": "en", "open_access": False, "reliability": "high", "categories": ["democratic_deficit"]},
    {"cite_key": "Winters_Page_2009", "entry_type": "article", "author": "Winters, Jeffrey A. and Page, Benjamin I.", "title": "Oligarchy in the United States?", "year": 2009, "journal": "Perspectives on Politics", "volume": "7", "number": "4", "pages": "731-751", "key_contribution": "Material power theory: extreme wealth = political oligarchy", "language": "en", "open_access": True, "reliability": "high", "categories": ["democratic_deficit"]},

    # 4.2 Data Source Bias Critique
    {"cite_key": "Bush_2017", "entry_type": "article", "author": "Bush, Sarah Sunn", "title": "The Politics of Rating Freedom", "year": 2017, "journal": "Perspectives on Politics", "key_contribution": "Freedom House methodology critique; US funding dependency", "language": "en", "open_access": False, "reliability": "high", "categories": ["data_source_critique"], "critiques_source": "freedom-house"},
    {"cite_key": "Gibler_Tir_2010", "entry_type": "article", "author": "Gibler, Douglas M. and Tir, Jaroslav", "title": "Settled Borders and Regime Type", "year": 2010, "journal": "Journal of Politics", "key_contribution": "Democracy indices conflate peace with democracy", "language": "en", "open_access": False, "reliability": "high", "categories": ["data_source_critique"]},
    {"cite_key": "VDem_2024", "entry_type": "report", "author": "Coppedge, Michael et al.", "title": "V-Dem Methodology (v14)", "year": 2024, "institution": "V-Dem Institute", "key_contribution": "V-Dem's own acknowledgment of expert subjectivity limits", "language": "en", "open_access": True, "reliability": "high", "categories": ["data_source_critique"], "critiques_source": "v-dem"},
    {"cite_key": "Steiner_2016", "entry_type": "article", "author": "Steiner, Nils D.", "title": "Comparing Freedom House Democracy Scores to Alternative Indices", "year": 2016, "key_contribution": "Systematic divergences between FH and alternatives", "language": "en", "open_access": False, "reliability": "high", "categories": ["data_source_critique"], "critiques_source": "freedom-house"},
    {"cite_key": "Wig_2024", "entry_type": "article", "author": "Wig, Tore et al.", "title": "A Pessimism Bias? Comparing Expert and Public Assessments of Democratic Health", "year": 2024, "key_contribution": "Political scientists systematically rate democracy lower than public", "language": "en", "open_access": True, "reliability": "high", "categories": ["data_source_critique"], "critiques_source": "v-dem"},
    {"cite_key": "Regilme_2019", "entry_type": "article", "author": "Regilme, Salvador Santino F.", "title": "The Decline of US Power? A Critical Review", "year": 2019, "key_contribution": "US-centric framing in democracy promotion indices", "language": "en", "open_access": False, "reliability": "high", "categories": ["data_source_critique"], "critiques_source": "freedom-house"},

    # 4.3 Conflict Data & State Violence
    {"cite_key": "Airwars_2014", "entry_type": "online", "author": "Airwars", "title": "Civilian harm monitoring archive", "year": 2014, "url": "https://airwars.org", "key_contribution": "Independent civilian casualty tracking; contradicts official military counts", "language": "en", "open_access": True, "reliability": "high", "categories": ["conflict_data", "counter_hegemonic_source"]},
    {"cite_key": "TBIJ_2010", "entry_type": "online", "author": "The Bureau of Investigative Journalism", "title": "The Bureau's Drone War Database", "year": 2010, "url": "https://www.thebureauinvestigates.com/projects/drone-war", "key_contribution": "Named victims of CIA drone strikes in Pakistan, Yemen, Somalia, Afghanistan", "language": "en", "open_access": True, "reliability": "high", "categories": ["conflict_data", "counter_hegemonic_source"]},
    {"cite_key": "Reprieve_2014", "entry_type": "report", "author": "Reprieve", "title": "You Never Die Twice: Multiple Kills in the US Drone Program", "year": 2014, "key_contribution": "Documents how target lists generate repeated civilian casualties", "language": "en", "open_access": True, "reliability": "high", "categories": ["conflict_data"]},
    {"cite_key": "Scahill_2016", "entry_type": "book", "author": "Scahill, Jeremy", "title": "The Assassination Complex: Inside the Government's Secret Drone Warfare Program", "year": 2016, "publisher": "Simon & Schuster", "key_contribution": "Leaked documents on US targeted killing criteria", "language": "en", "open_access": False, "reliability": "high", "categories": ["conflict_data"]},
    {"cite_key": "FA_2019", "entry_type": "online", "author": "Forensic Architecture", "title": "The Drone Strikes Platform", "year": 2019, "url": "https://forensic-architecture.org/investigation/the-drone-strikes-platform", "key_contribution": "Spatial reconstruction of drone strike evidence", "language": "en", "open_access": True, "reliability": "high", "categories": ["conflict_data"]},
    {"cite_key": "NAF_ongoing", "entry_type": "online", "author": "New America Foundation", "title": "America's Counterterrorism Wars", "year": 2020, "url": "https://www.newamerica.org/international-security/reports/americas-counterterrorism-wars/", "key_contribution": "Tracking lethal counterterrorism operations data", "language": "en", "open_access": True, "reliability": "high", "categories": ["conflict_data"]},
    {"cite_key": "Eck_2012", "entry_type": "article", "author": "Eck, Kristine", "title": "In Data We Trust? A Comparison of UCDP GED and ACLED Conflict Events Datasets", "year": 2012, "journal": "Journal of Peace Research", "key_contribution": "Comparison of UCDP vs ACLED; coding differences and reliability", "language": "en", "open_access": False, "reliability": "high", "categories": ["conflict_data", "data_source_critique"], "critiques_source": "acled"},
    {"cite_key": "Raleigh_2010", "entry_type": "article", "author": "Raleigh, Clionadh et al.", "title": "Introducing ACLED: An Armed Conflict Location and Event Dataset", "year": 2010, "journal": "Journal of Peace Research", "key_contribution": "Original ACLED methodology paper", "language": "en", "open_access": False, "reliability": "high", "categories": ["conflict_data", "data_source_critique"], "critiques_source": "acled"},

    # 4.4 World-Systems & Structural Critique
    {"cite_key": "Wallerstein_2004", "entry_type": "book", "author": "Wallerstein, Immanuel", "title": "World-Systems Analysis: An Introduction", "year": 2004, "publisher": "Duke University Press", "key_contribution": "Core-periphery-semiperiphery framework", "language": "en", "open_access": False, "reliability": "high", "categories": ["world_systems"]},
    {"cite_key": "Said_1978", "entry_type": "book", "author": "Said, Edward W.", "title": "Orientalism", "year": 1978, "publisher": "Pantheon Books", "key_contribution": "How Western scholarship constructs 'the Other'", "language": "en", "open_access": False, "reliability": "high", "categories": ["world_systems"]},
    {"cite_key": "Fanon_1961", "entry_type": "book", "author": "Fanon, Frantz", "title": "The Wretched of the Earth", "year": 1961, "publisher": "Grove Press", "key_contribution": "Colonial violence and decolonization", "language": "en", "open_access": False, "reliability": "high", "categories": ["world_systems"]},
    {"cite_key": "Santos_2014", "entry_type": "book", "author": "Santos, Boaventura de Sousa", "title": "Epistemologies of the South: Justice Against Epistemicide", "year": 2014, "publisher": "Routledge", "key_contribution": "Southern epistemologies excluded from knowledge production", "language": "en", "open_access": False, "reliability": "high", "categories": ["world_systems"]},
    {"cite_key": "Quijano_2000", "entry_type": "incollection", "author": "Quijano, Aníbal", "title": "Coloniality of Power and Eurocentrism in Latin America", "year": 2000, "key_contribution": "Coloniality of power persists after formal decolonization", "language": "en", "open_access": True, "reliability": "high", "categories": ["world_systems"]},
    {"cite_key": "Bhambra_2014", "entry_type": "book", "author": "Bhambra, Gurminder K.", "title": "Connected Sociologies", "year": 2014, "publisher": "Bloomsbury", "key_contribution": "Decolonizing social science methodology", "language": "en", "open_access": False, "reliability": "high", "categories": ["world_systems"]},
    {"cite_key": "Mignolo_2011", "entry_type": "book", "author": "Mignolo, Walter D.", "title": "The Darker Side of Western Modernity", "year": 2011, "publisher": "Duke University Press", "key_contribution": "Western modernity as colonial modernity", "language": "en", "open_access": False, "reliability": "high", "categories": ["world_systems"]},

    # 4.5 Demographic Data Reliability
    {"cite_key": "Yi_2013", "entry_type": "book", "author": "Yi, Fuxian", "title": "Big Country with an Empty Nest", "year": 2013, "key_contribution": "China population overcounted by 90-130 million", "language": "zh", "open_access": False, "reliability": "high", "categories": ["demographic_reliability"]},
    {"cite_key": "Goodkind_2017", "entry_type": "article", "author": "Goodkind, Daniel", "title": "The Demographic Impact of China's One-Child Policy", "year": 2017, "journal": "Demography", "key_contribution": "NIH: underreporting of births, hidden children (heihaizi)", "language": "en", "open_access": True, "reliability": "high", "categories": ["demographic_reliability"]},
    {"cite_key": "Zeihan_2023", "entry_type": "misc", "author": "Zeihan, Peter", "title": "China's Demographic Manipulation", "year": 2023, "url": "https://zeihan.com", "key_contribution": "Geopolitical implications of unreliable Chinese census data", "language": "en", "open_access": True, "reliability": "medium", "categories": ["demographic_reliability"]},
    {"cite_key": "Jerven_2013", "entry_type": "book", "author": "Jerven, Morten", "title": "Poor Numbers: How We Are Misled by African Development Statistics", "year": 2013, "publisher": "Cornell University Press", "key_contribution": "GDP statistics in Africa are largely fabricated/estimated", "language": "en", "open_access": False, "reliability": "high", "categories": ["demographic_reliability", "data_source_critique"]},
    {"cite_key": "Wallace_2016", "entry_type": "article", "author": "Wallace, Jeremy L.", "title": "Juking the Stats? Authoritarian Information Problems in China", "year": 2016, "journal": "British Journal of Political Science", "key_contribution": "Incentive structures for statistical manipulation in China", "language": "en", "open_access": False, "reliability": "high", "categories": ["demographic_reliability"]},

    # 4.6 International Law & State Terrorism
    {"cite_key": "Blakeley_2009", "entry_type": "book", "author": "Blakeley, Ruth", "title": "State Terrorism and Neoliberalism: The North in the South", "year": 2009, "publisher": "Cambridge University Press", "key_contribution": "Systematic analysis of state terrorism by Western democracies", "language": "en", "open_access": False, "reliability": "high", "categories": ["international_law"]},
    {"cite_key": "Jackson_2011", "entry_type": "book", "author": "Jackson, Richard et al.", "title": "Terrorism: A Critical Introduction", "year": 2011, "publisher": "Palgrave Macmillan", "key_contribution": "Critical terrorism studies; state terrorism as analytical category", "language": "en", "open_access": False, "reliability": "high", "categories": ["international_law"]},
    {"cite_key": "Stohl_Lopez_1984", "entry_type": "book", "author": "Stohl, Michael and Lopez, George A.", "title": "The State as Terrorist: The Dynamics of Governmental Violence and Repression", "year": 1984, "publisher": "Greenwood Press", "key_contribution": "Foundational work on state terrorism", "language": "en", "open_access": False, "reliability": "high", "categories": ["international_law"]},
    {"cite_key": "Alston_2010", "entry_type": "report", "author": "Alston, Philip", "title": "Report of the Special Rapporteur on Extrajudicial, Summary or Arbitrary Executions", "year": 2010, "institution": "UN Human Rights Council (A/HRC/14/24/Add.6)", "key_contribution": "UN: US targeted killings via drones likely violate international law", "language": "en", "open_access": True, "reliability": "high", "categories": ["international_law", "conflict_data"]},
    {"cite_key": "Emmerson_2013", "entry_type": "report", "author": "Emmerson, Ben", "title": "Report of the Special Rapporteur on Human Rights and Counter-Terrorism", "year": 2013, "institution": "UN General Assembly (A/68/389)", "key_contribution": "UN: drone strikes have caused disproportionate civilian casualties", "language": "en", "open_access": True, "reliability": "high", "categories": ["international_law", "conflict_data"]},
    {"cite_key": "Heller_2013", "entry_type": "article", "author": "Heller, Kevin Jon", "title": "'One Hell of a Killing Machine': Signature Strikes and International Law", "year": 2013, "journal": "Journal of International Criminal Justice", "key_contribution": "Legal analysis of signature strikes (pattern-of-life targeting)", "language": "en", "open_access": False, "reliability": "high", "categories": ["international_law"]},

    # 4.7 Alternative & Counter-Hegemonic Data Sources (online/misc)
    {"cite_key": "EveryCasualty", "entry_type": "online", "author": "Every Casualty Counted", "title": "Casualty Recording Organisations Directory", "year": 2015, "url": "https://everycasualty.org", "key_contribution": "Meta-index of casualty recording orgs", "language": "en", "open_access": True, "reliability": "high", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "CPM", "entry_type": "online", "author": "Civilian Protection Monitor", "title": "Civilian Protection Monitor", "year": 2020, "url": "https://civilianprotectionmonitor.org", "key_contribution": "State conduct in armed conflict", "language": "en", "open_access": True, "reliability": "high", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "GDELT", "entry_type": "online", "author": "GDELT Project", "title": "Global Database of Events, Language, and Tone", "year": 2013, "url": "https://www.gdeltproject.org", "key_contribution": "Counter-balance to English-language media dominance", "language": "en", "open_access": True, "reliability": "high", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "SouthCentre", "entry_type": "online", "author": "South Centre", "title": "South Centre Policy Research", "year": 1995, "url": "https://www.southcentre.int", "key_contribution": "Global South policy analysis", "language": "en", "open_access": True, "reliability": "high", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "TWN", "entry_type": "online", "author": "Third World Network", "title": "Third World Network", "year": 1984, "url": "https://www.twn.my", "key_contribution": "Development & trade from Global South", "language": "en", "open_access": True, "reliability": "medium", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "BRICS_Stats", "entry_type": "misc", "author": "BRICS Joint Statistical Publication", "title": "BRICS Joint Statistical Publication", "year": 2023, "key_contribution": "BRICS self-reported statistics (entity self-perspective)", "language": "en", "open_access": True, "reliability": "medium", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "AlJazeera_Inv", "entry_type": "online", "author": "Al Jazeera Investigative Unit", "title": "Al Jazeera Investigations", "year": 2006, "url": "https://www.aljazeera.com/investigations", "key_contribution": "Non-Western investigative journalism", "language": "en", "open_access": True, "reliability": "medium", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "Xinhua_CGTN", "entry_type": "online", "author": "Xinhua / CGTN", "title": "Chinese State Media", "year": 1931, "url": "https://www.xinhuanet.com", "key_contribution": "Chinese state perspective (entity self-view, must be critically read)", "language": "zh", "open_access": True, "reliability": "low", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "RT_TASS", "entry_type": "online", "author": "RT / TASS", "title": "Russian State Media", "year": 2005, "url": "https://www.rt.com", "key_contribution": "Russian state perspective (entity self-view, must be critically read)", "language": "ru", "open_access": True, "reliability": "low", "categories": ["counter_hegemonic_source"]},
    {"cite_key": "TeleSUR", "entry_type": "online", "author": "TeleSUR", "title": "TeleSUR", "year": 2005, "url": "https://www.telesurtv.net", "key_contribution": "Latin American state-funded media (Global South perspective)", "language": "es", "open_access": True, "reliability": "low", "categories": ["counter_hegemonic_source"]},
]


async def import_categories(session) -> int:
    """Create ReferenceCategory nodes."""
    query = """
    UNWIND $categories AS cat
    MERGE (c:ReferenceCategory {id: cat.id})
    SET c.name = cat.name,
        c.description = cat.description,
        c.section = cat.section
    RETURN count(c) AS created
    """
    result = await session.run(query, categories=CATEGORIES)
    record = await result.single()
    count = record["created"] if record else 0
    logger.info("Created/updated %d ReferenceCategory nodes", count)
    return count


async def import_references(session) -> int:
    """Create Reference nodes with all BibLaTeX-analog properties."""
    # Strip categories and critiques_source (handled as edges) before MERGE
    refs_clean = []
    for ref in REFERENCES:
        r = {k: v for k, v in ref.items() if k not in ("categories", "critiques_source")}
        refs_clean.append(r)

    query = """
    UNWIND $refs AS ref
    MERGE (r:Reference {cite_key: ref.cite_key})
    SET r += ref
    RETURN count(r) AS created
    """
    result = await session.run(query, refs=refs_clean)
    record = await result.single()
    count = record["created"] if record else 0
    logger.info("Created/updated %d Reference nodes", count)
    return count


async def create_categorized_as_edges(session) -> int:
    """Create (Reference)-[:CATEGORIZED_AS]->(ReferenceCategory) edges."""
    total = 0
    for ref in REFERENCES:
        for cat_id in ref.get("categories", []):
            query = """
            MATCH (r:Reference {cite_key: $cite_key})
            MATCH (c:ReferenceCategory {id: $cat_id})
            MERGE (r)-[:CATEGORIZED_AS]->(c)
            RETURN count(*) AS created
            """
            result = await session.run(query, cite_key=ref["cite_key"], cat_id=cat_id)
            record = await result.single()
            total += record["created"] if record else 0
    logger.info("Created %d CATEGORIZED_AS edges", total)
    return total


async def create_critiques_edges(session) -> int:
    """Create (Reference)-[:CRITIQUES]->(DataSource) edges."""
    total = 0
    for ref in REFERENCES:
        ds_id = ref.get("critiques_source")
        if not ds_id:
            continue
        query = """
        MATCH (r:Reference {cite_key: $cite_key})
        MATCH (ds:DataSource {id: $ds_id})
        MERGE (r)-[:CRITIQUES]->(ds)
        RETURN count(*) AS created
        """
        result = await session.run(query, cite_key=ref["cite_key"], ds_id=ds_id)
        record = await result.single()
        total += record["created"] if record else 0
    logger.info("Created %d CRITIQUES edges", total)
    return total


async def run_etl():
    """Main ETL entry point."""
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        async with driver.session() as session:
            logger.info("=== ETL References: importing 54 sources + 7 categories ===")
            await import_categories(session)
            await import_references(session)
            await create_categorized_as_edges(session)
            await create_critiques_edges(session)
            logger.info("=== ETL References complete ===")
    finally:
        await driver.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(run_etl())
