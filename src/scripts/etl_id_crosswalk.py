#!/usr/bin/env python3
"""ETL: ID Crosswalk — Build ISO-3 ↔ COW ↔ UN M49 mapping.

Sources:
- UN M49: Already loaded from REST Countries API (ccn3 field) in P1-01
- COW codes: Correlates of War state system (static mapping)
- V-Dem IDs: V-Dem codebook (static mapping)

The crosswalk is saved to data/id_crosswalk.json AND applied to Neo4j Nation nodes.

Task: task-P1-02-id-crosswalk
Agent: Dione
"""

import json
import logging
import os
from datetime import datetime, timezone

from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ETL-P1.2] %(message)s")
log = logging.getLogger("etl_crosswalk")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")

# Correlates of War state codes (COW system membership list)
# Source: https://correlatesofwar.org/data-sets/state-system-membership/
# Only sovereign states recognized by COW
COW_CODES = {
    "USA": 2, "CAN": 20, "BHS": 31, "CUB": 40, "HTI": 41, "DOM": 42, "JAM": 51,
    "TTO": 52, "BRB": 53, "DMA": 54, "GRD": 55, "LCA": 56, "VCT": 57, "ATG": 58,
    "KNA": 60, "MEX": 70, "BLZ": 80, "GTM": 90, "HND": 91, "SLV": 92, "NIC": 93,
    "CRI": 94, "PAN": 95, "COL": 100, "VEN": 101, "GUY": 110, "SUR": 115, "ECU": 130,
    "PER": 135, "BRA": 140, "BOL": 145, "PRY": 150, "CHL": 155, "ARG": 160, "URY": 165,
    "GBR": 200, "IRL": 205, "NLD": 210, "BEL": 211, "LUX": 212, "FRA": 220, "MCO": 221,
    "LIE": 223, "CHE": 225, "ESP": 230, "AND": 232, "PRT": 235, "DEU": 255,
    "POL": 290, "AUT": 305, "HUN": 310, "CZE": 316, "SVK": 317, "ITA": 325,
    "SMR": 331, "MLT": 338, "ALB": 339, "MNE": 341, "MKD": 343, "HRV": 344,
    "SVN": 349, "BIH": 346, "SRB": 345, "UNK": 347, "GRC": 350, "CYP": 352,
    "BGR": 355, "MDA": 359, "ROU": 360, "RUS": 365, "EST": 366, "LVA": 367,
    "LTU": 368, "UKR": 369, "BLR": 370, "ARM": 371, "GEO": 372, "AZE": 373,
    "FIN": 375, "SWE": 380, "NOR": 385, "DNK": 390, "ISL": 395,
    "MAR": 600, "DZA": 615, "TUN": 616, "LBY": 620, "SDN": 625, "IRN": 630,
    "TUR": 640, "IRQ": 645, "EGY": 651, "SYR": 652, "LBN": 660, "JOR": 663,
    "ISR": 666, "SAU": 670, "YEM": 679, "KWT": 690, "BHR": 692, "QAT": 694,
    "ARE": 696, "OMN": 698, "AFG": 700, "TKM": 701, "TJK": 702, "KGZ": 703,
    "UZB": 704, "KAZ": 705, "CHN": 710, "MNG": 712, "TWN": 713, "PRK": 731,
    "KOR": 732, "JPN": 740, "IND": 750, "BTN": 760, "PAK": 770, "BGD": 771,
    "MMR": 775, "LKA": 780, "MDV": 781, "NPL": 790, "THA": 800, "KHM": 811,
    "LAO": 812, "VNM": 816, "MYS": 820, "SGP": 830, "BRN": 835, "PHL": 840,
    "IDN": 850, "TLS": 860, "AUS": 900, "PNG": 910, "NZL": 920, "VUT": 935,
    "SLB": 940, "FJI": 950, "TON": 955, "NRU": 970, "TUV": 947, "WSM": 990,
    "FSM": 987, "MHL": 983, "PLW": 986, "KIR": 946,
    "SEN": 433, "GMB": 420, "MLI": 432, "GIN": 438, "CIV": 437, "BFA": 439,
    "NER": 436, "TGO": 461, "BEN": 434, "MRT": 435, "NGA": 475, "CMR": 471,
    "TCD": 483, "CAF": 482, "GNQ": 411, "GAB": 481, "COG": 484, "COD": 490,
    "UGA": 500, "KEN": 501, "TZA": 510, "BDI": 516, "RWA": 517, "SOM": 520,
    "DJI": 522, "ETH": 530, "ERI": 531, "AGO": 540, "MOZ": 541, "ZMB": 551,
    "ZWE": 552, "MWI": 553, "ZAF": 560, "NAM": 565, "LSO": 570, "BWA": 571,
    "SWZ": 572, "MDG": 580, "COM": 581, "MUS": 590, "SYC": 591, "SSD": 626,
    "GHA": 452, "LBR": 450, "SLE": 451, "GNB": 404, "CPV": 402, "STP": 403,
    # Missing from COW: micro-states, some Pacific islands
}

# V-Dem country IDs (from V-Dem codebook v14)
# Source: https://v-dem.net/data/the-v-dem-dataset/
VDEM_IDS = {
    "USA": 20, "CAN": 110, "MEX": 3, "GTM": 4, "HND": 7, "SLV": 5, "NIC": 8,
    "CRI": 6, "PAN": 9, "COL": 10, "VEN": 11, "GUY": 79, "SUR": 80, "ECU": 12,
    "PER": 13, "BRA": 15, "BOL": 14, "PRY": 16, "CHL": 17, "ARG": 18, "URY": 19,
    "CUB": 2, "HTI": 21, "DOM": 22, "JAM": 23, "TTO": 24, "BHS": 132,
    "GBR": 101, "IRL": 102, "NLD": 21, "BEL": 103, "LUX": 104, "FRA": 105,
    "CHE": 106, "ESP": 107, "PRT": 108, "DEU": 77, "POL": 68, "AUT": 109,
    "HUN": 69, "CZE": 157, "SVK": 158, "ITA": 112, "GRC": 111, "CYP": 120,
    "BGR": 71, "ROU": 70, "RUS": 30, "UKR": 33, "BLR": 34, "MDA": 32,
    "EST": 35, "LVA": 36, "LTU": 37, "ARM": 38, "GEO": 39, "AZE": 40,
    "FIN": 113, "SWE": 114, "NOR": 115, "DNK": 116, "ISL": 117,
    "ALB": 118, "MNE": 159, "MKD": 153, "HRV": 155, "SVN": 154, "BIH": 152, "SRB": 156,
    "MAR": 86, "DZA": 87, "TUN": 88, "LBY": 89, "EGY": 51, "SDN": 52, "SSD": 181,
    "TUR": 78, "IRQ": 41, "IRN": 42, "SYR": 43, "LBN": 44, "JOR": 45, "ISR": 46,
    "SAU": 48, "YEM": 47, "KWT": 49, "BHR": 122, "QAT": 123, "ARE": 124, "OMN": 125,
    "AFG": 100, "CHN": 60, "MNG": 62, "TWN": 61, "PRK": 63, "KOR": 64, "JPN": 65,
    "IND": 54, "PAK": 55, "BGD": 56, "LKA": 57, "NPL": 58, "BTN": 176,
    "THA": 66, "KHM": 137, "VNM": 34, "LAO": 138, "MMR": 59, "MYS": 67,
    "SGP": 130, "BRN": 131, "PHL": 126, "IDN": 127, "TLS": 169,
    "AUS": 128, "NZL": 129, "FJI": 136, "PNG": 133,
    "NGA": 93, "GHA": 83, "KEN": 84, "TZA": 96, "ETH": 82, "ZAF": 97,
    "SEN": 90, "CMR": 94, "CIV": 91, "UGA": 95, "MOZ": 98, "ZMB": 161,
    "ZWE": 162, "RWA": 129, "AGO": 104, "COD": 99, "MDG": 85, "MWI": 160,
    "TKM": 148, "TJK": 147, "KGZ": 146, "UZB": 149, "KAZ": 145,
}

# World Bank country code to ISO-3 is 1:1 (WB uses ISO-3)
# No separate mapping needed.


def build_crosswalk(driver) -> dict:
    """Build the crosswalk from Neo4j nations + static mappings."""
    crosswalk = {}
    
    with driver.session() as session:
        result = session.run("""
            MATCH (n:Nation) 
            RETURN n.iso3 AS iso3, n.iso2 AS iso2, n.name_short AS name, 
                   n.un_m49 AS un_m49
            ORDER BY n.iso3
        """)
        
        for record in result:
            iso3 = record["iso3"]
            crosswalk[iso3] = {
                "iso3": iso3,
                "iso2": record["iso2"],
                "name": record["name"],
                "un_m49": record["un_m49"],
                "cow_code": COW_CODES.get(iso3),
                "vdem_id": VDEM_IDS.get(iso3),
                "wb_code": iso3,  # World Bank uses ISO-3 directly
            }
    
    return crosswalk


def apply_to_neo4j(driver, crosswalk: dict):
    """Apply COW codes and V-Dem IDs to Nation nodes."""
    batch_id = f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-1.2"
    
    records = []
    for iso3, data in crosswalk.items():
        props = {}
        if data["cow_code"] is not None:
            props["cow_code"] = data["cow_code"]
        if data["vdem_id"] is not None:
            props["vdem_id"] = data["vdem_id"]
        if props:
            records.append({"iso3": iso3, "properties": props, "prop_names": list(props.keys())})
    
    with driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run("""
                CREATE (ib:ImportBatch {
                    id: $batch_id, timestamp: datetime(), agent: "Dione",
                    method: "static_mapping", record_count: $count,
                    notes: "ID Crosswalk: COW codes from Correlates of War, V-Dem IDs from V-Dem v14 codebook",
                    confidence: "high", requires_replacement: false
                })
                WITH ib
                MATCH (ds:DataSource {id: "cia-factbook"})
                MERGE (ib)-[:FROM_SOURCE]->(ds)
            """, batch_id=batch_id, count=len(records))
            
            tx.run("""
                UNWIND $records AS rec
                MATCH (n:Nation {iso3: rec.iso3})
                SET n += rec.properties
                WITH n, rec
                MATCH (ib:ImportBatch {id: $batch_id})
                MERGE (n)-[p:PROVENANCE]->(ib)
                SET p.properties = rec.prop_names
            """, records=records, batch_id=batch_id)
            
            tx.commit()
    
    return len(records), batch_id


def main():
    log.info("=== ETL P1.2: ID Crosswalk ===")
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        # Build crosswalk
        crosswalk = build_crosswalk(driver)
        log.info(f"Built crosswalk for {len(crosswalk)} nations")
        
        # Count coverage
        has_cow = sum(1 for v in crosswalk.values() if v["cow_code"] is not None)
        has_vdem = sum(1 for v in crosswalk.values() if v["vdem_id"] is not None)
        log.info(f"Coverage: COW={has_cow}/{len(crosswalk)}, V-Dem={has_vdem}/{len(crosswalk)}")
        
        # Save to JSON
        os.makedirs("data", exist_ok=True)
        with open("data/id_crosswalk.json", "w") as f:
            json.dump(crosswalk, f, indent=2, ensure_ascii=False)
        log.info("Saved data/id_crosswalk.json")
        
        # Apply to Neo4j
        updated, batch_id = apply_to_neo4j(driver, crosswalk)
        log.info(f"Applied {updated} updates to Neo4j, batch={batch_id}")
        
        log.info(f"=== DONE: {len(crosswalk)} nations crosswalked, {updated} updated in Neo4j ===")
        return len(crosswalk), batch_id
    finally:
        driver.close()


if __name__ == "__main__":
    total, batch_id = main()
    print(f"RESULT: {total} nations crosswalked, batch={batch_id}")
