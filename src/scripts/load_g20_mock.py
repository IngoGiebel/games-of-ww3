import os
import logging
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Database Connection Configuration ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gww3-dev-2026")
DATA_QUALITY_TAG = 'mock_realistic'

# --- Mock Data Definitions ---

# G20 Nations (plus EU). USA and CHN are assumed to exist but are referenced in relationships.
NATIONS_DATA = [
    # Americas
    {
        "iso3": "ARG", "iso2": "AR", "name": "Argentine Republic", "name_short": "Argentina", "cow_code": 160, "un_m49": 32,
        "population": 46_000_000, "gdp_nominal": 650_000_000_000, "gdp_growth": -2.5, "gdp_per_capita": 14130,
        "inflation_rate": 250.0, "unemployment": 7.8, "gini": 42.3, "debt_to_gdp": 85.0, "forex_reserves": 27_000_000_000,
        "military_spending_pct_gdp": 0.8, "military_spending_abs": 5_200_000_000, "manpower_active": 83_000, "manpower_reserve": 40_000,
        "nuclear_warheads": 0, "nuclear_status": 'capable', "government_type": "Presidential republic", "stability_index": 35,
        "freedom_house_score": 77, "corruption_index": 37, "press_freedom": 66, "internet_penetration": 85.0, "urbanization": 92.0,
        "leader_name": "Javier Milei", "leader_ideology": "Right-wing libertarianism", "national_morale": 45, "war_weariness": 25,
        "region": "Americas", "sub_region": "South America"
    },
    {
        "iso3": "BRA", "iso2": "BR", "name": "Federative Republic of Brazil", "name_short": "Brazil", "cow_code": 140, "un_m49": 76,
        "population": 216_000_000, "gdp_nominal": 2_300_000_000_000, "gdp_growth": 2.2, "gdp_per_capita": 10650,
        "inflation_rate": 4.5, "unemployment": 8.0, "gini": 48.9, "debt_to_gdp": 75.0, "forex_reserves": 340_000_000_000,
        "military_spending_pct_gdp": 1.4, "military_spending_abs": 32_200_000_000, "manpower_active": 360_000, "manpower_reserve": 1_340_000,
        "nuclear_warheads": 0, "nuclear_status": 'capable', "government_type": "Federal presidential republic", "stability_index": 50,
        "freedom_house_score": 71, "corruption_index": 36, "press_freedom": 87, "internet_penetration": 81.0, "urbanization": 87.0,
        "leader_name": "Luiz Inácio Lula da Silva", "leader_ideology": "Social democracy", "national_morale": 65, "war_weariness": 15,
        "region": "Americas", "sub_region": "South America"
    },
    {
        "iso3": "CAN", "iso2": "CA", "name": "Canada", "name_short": "Canada", "cow_code": 20, "un_m49": 124,
        "population": 40_000_000, "gdp_nominal": 2_300_000_000_000, "gdp_growth": 1.0, "gdp_per_capita": 57500,
        "inflation_rate": 3.1, "unemployment": 5.8, "gini": 30.3, "debt_to_gdp": 106.0, "forex_reserves": 110_000_000_000,
        "military_spending_pct_gdp": 1.3, "military_spending_abs": 29_900_000_000, "manpower_active": 70_000, "manpower_reserve": 55_000,
        "nuclear_warheads": 0, "nuclear_status": 'non_nuclear', "government_type": "Federal parliamentary constitutional monarchy", "stability_index": 85,
        "freedom_house_score": 96, "corruption_index": 76, "press_freedom": 14, "internet_penetration": 94.0, "urbanization": 82.0,
        "leader_name": "Justin Trudeau", "leader_ideology": "Liberalism", "national_morale": 70, "war_weariness": 30,
        "region": "Americas", "sub_region": "Northern America"
    },
    {
        "iso3": "MEX", "iso2": "MX", "name": "United Mexican States", "name_short": "Mexico", "cow_code": 70, "un_m49": 484,
        "population": 128_000_000, "gdp_nominal": 1_800_000_000_000, "gdp_growth": 3.0, "gdp_per_capita": 14060,
        "inflation_rate": 4.7, "unemployment": 3.0, "gini": 45.4, "debt_to_gdp": 49.0, "forex_reserves": 205_000_000_000,
        "military_spending_pct_gdp": 0.7, "military_spending_abs": 12_600_000_000, "manpower_active": 250_000, "manpower_reserve": 80_000,
        "nuclear_warheads": 0, "nuclear_status": 'non_nuclear', "government_type": "Federal presidential republic", "stability_index": 45,
        "freedom_house_score": 61, "corruption_index": 31, "press_freedom": 121, "internet_penetration": 78.0, "urbanization": 81.0,
        "leader_name": "Claudia Sheinbaum", "leader_ideology": "Left-wing populism", "national_morale": 60, "war_weariness": 40,
        "region": "Americas", "sub_region": "Central America"
    },
    # Europe
    {
        "iso3": "DEU", "iso2": "DE", "name": "Federal Republic of Germany", "name_short": "Germany", "cow_code": 255, "un_m49": 276,
        "population": 84_000_000, "gdp_nominal": 4_700_000_000_000, "gdp_growth": -0.3, "gdp_per_capita": 56000,
        "inflation_rate": 3.5, "unemployment": 5.9, "gini": 31.7, "debt_to_gdp": 65.0, "forex_reserves": 290_000_000_000,
        "military_spending_pct_gdp": 2.1, "military_spending_abs": 98_700_000_000, "manpower_active": 184_000, "manpower_reserve": 90_000,
        "nuclear_warheads": 0, "nuclear_status": 'capable', "government_type": "Federal parliamentary republic", "stability_index": 78,
        "freedom_house_score": 93, "corruption_index": 79, "press_freedom": 10, "internet_penetration": 93.0, "urbanization": 78.0,
        "leader_name": "Olaf Scholz", "leader_ideology": "Social democracy", "national_morale": 60, "war_weariness": 55,
        "region": "Europe", "sub_region": "Western Europe"
    },
    {
        "iso3": "FRA", "iso2": "FR", "name": "French Republic", "name_short": "France", "cow_code": 220, "un_m49": 250,
        "population": 66_000_000, "gdp_nominal": 3_100_000_000_000, "gdp_growth": 0.8, "gdp_per_capita": 47000,
        "inflation_rate": 4.1, "unemployment": 7.4, "gini": 32.7, "debt_to_gdp": 112.0, "forex_reserves": 240_000_000_000,
        "military_spending_pct_gdp": 1.9, "military_spending_abs": 58_900_000_000, "manpower_active": 205_000, "manpower_reserve": 40_000,
        "nuclear_warheads": 290, "nuclear_status": 'armed', "government_type": "Unitary semi-presidential republic", "stability_index": 70,
        "freedom_house_score": 89, "corruption_index": 71, "press_freedom": 21, "internet_penetration": 92.0, "urbanization": 81.0,
        "leader_name": "Emmanuel Macron", "leader_ideology": "Centrism", "national_morale": 62, "war_weariness": 50,
        "region": "Europe", "sub_region": "Western Europe"
    },
    {
        "iso3": "GBR", "iso2": "GB", "name": "United Kingdom", "name_short": "United Kingdom", "cow_code": 200, "un_m49": 826,
        "population": 67_000_000, "gdp_nominal": 3_500_000_000_000, "gdp_growth": 0.5, "gdp_per_capita": 52200,
        "inflation_rate": 4.2, "unemployment": 4.3, "gini": 35.1, "debt_to_gdp": 101.0, "forex_reserves": 180_000_000_000,
        "military_spending_pct_gdp": 2.3, "military_spending_abs": 80_500_000_000, "manpower_active": 194_000, "manpower_reserve": 80_000,
        "nuclear_warheads": 225, "nuclear_status": 'armed', "government_type": "Unitary parliamentary constitutional monarchy", "stability_index": 75,
        "freedom_house_score": 88, "corruption_index": 73, "press_freedom": 23, "internet_penetration": 95.0, "urbanization": 84.0,
        "leader_name": "Keir Starmer", "leader_ideology": "Social democracy", "national_morale": 65, "war_weariness": 45,
        "region": "Europe", "sub_region": "Northern Europe"
    },
    {
        "iso3": "ITA", "iso2": "IT", "name": "Italian Republic", "name_short": "Italy", "cow_code": 325, "un_m49": 380,
        "population": 59_000_000, "gdp_nominal": 2_300_000_000_000, "gdp_growth": 0.7, "gdp_per_capita": 39000,
        "inflation_rate": 1.8, "unemployment": 7.3, "gini": 35.2, "debt_to_gdp": 145.0, "forex_reserves": 230_000_000_000,
        "military_spending_pct_gdp": 1.6, "military_spending_abs": 36_800_000_000, "manpower_active": 170_000, "manpower_reserve": 20_000,
        "nuclear_warheads": 0, "nuclear_status": 'non_nuclear', "government_type": "Unitary parliamentary republic", "stability_index": 60,
        "freedom_house_score": 84, "corruption_index": 56, "press_freedom": 46, "internet_penetration": 84.0, "urbanization": 72.0,
        "leader_name": "Giorgia Meloni", "leader_ideology": "Right-wing populism", "national_morale": 58, "war_weariness": 35,
        "region": "Europe", "sub_region": "Southern Europe"
    },
    {
        "iso3": "RUS", "iso2": "RU", "name": "Russian Federation", "name_short": "Russia", "cow_code": 365, "un_m49": 643,
        "population": 144_000_000, "gdp_nominal": 2_100_000_000_000, "gdp_growth": 3.0, "gdp_per_capita": 14600,
        "inflation_rate": 7.5, "unemployment": 3.0, "gini": 36.0, "debt_to_gdp": 19.0, "forex_reserves": 580_000_000_000,
        "military_spending_pct_gdp": 6.5, "military_spending_abs": 136_500_000_000, "manpower_active": 1_320_000, "manpower_reserve": 2_000_000,
        "nuclear_warheads": 5977, "nuclear_status": 'armed', "government_type": "Federal semi-presidential republic", "stability_index": 25,
        "freedom_house_score": 13, "corruption_index": 26, "press_freedom": 162, "internet_penetration": 88.0, "urbanization": 75.0,
        "leader_name": "Vladimir Putin", "leader_ideology": "National conservatism", "national_morale": 75, "war_weariness": 60,
        "region": "Europe", "sub_region": "Eastern Europe"
    },
     {
        "iso3": "TUR", "iso2": "TR", "name": "Republic of Türkiye", "name_short": "Türkiye", "cow_code": 640, "un_m49": 792,
        "population": 85_000_000, "gdp_nominal": 1_300_000_000_000, "gdp_growth": 3.5, "gdp_per_capita": 15300,
        "inflation_rate": 70.0, "unemployment": 9.0, "gini": 41.9, "debt_to_gdp": 39.0, "forex_reserves": 130_000_000_000,
        "military_spending_pct_gdp": 2.0, "military_spending_abs": 26_000_000_000, "manpower_active": 425_000, "manpower_reserve": 380_000,
        "nuclear_warheads": 0, "nuclear_status": 'non_nuclear', "government_type": "Unitary presidential republic", "stability_index": 40,
        "freedom_house_score": 32, "corruption_index": 34, "press_freedom": 165, "internet_penetration": 83.0, "urbanization": 77.0,
        "leader_name": "Recep Tayyip Erdoğan", "leader_ideology": "National conservatism", "national_morale": 68, "war_weariness": 40,
        "region": "Asia", "sub_region": "Western Asia"
    },
    # Asia
    {
        "iso3": "IND", "iso2": "IN", "name": "Republic of India", "name_short": "India", "cow_code": 750, "un_m49": 356,
        "population": 1_420_000_000, "gdp_nominal": 4_100_000_000_000, "gdp_growth": 7.8, "gdp_per_capita": 2900,
        "inflation_rate": 5.7, "unemployment": 7.5, "gini": 35.7, "debt_to_gdp": 83.0, "forex_reserves": 600_000_000_000,
        "military_spending_pct_gdp": 2.4, "military_spending_abs": 98_400_000_000, "manpower_active": 1_450_000, "manpower_reserve": 1_150_000,
        "nuclear_warheads": 164, "nuclear_status": 'armed', "government_type": "Federal parliamentary republic", "stability_index": 55,
        "freedom_house_score": 66, "corruption_index": 39, "press_freedom": 159, "internet_penetration": 50.0, "urbanization": 36.0,
        "leader_name": "Narendra Modi", "leader_ideology": "Hindu nationalism", "national_morale": 80, "war_weariness": 20,
        "region": "Asia", "sub_region": "Southern Asia"
    },
    {
        "iso3": "IDN", "iso2": "ID", "name": "Republic of Indonesia", "name_short": "Indonesia", "cow_code": 850, "un_m49": 360,
        "population": 277_000_000, "gdp_nominal": 1_400_000_000_000, "gdp_growth": 5.0, "gdp_per_capita": 5050,
        "inflation_rate": 2.8, "unemployment": 5.3, "gini": 37.9, "debt_to_gdp": 40.0, "forex_reserves": 140_000_000_000,
        "military_spending_pct_gdp": 0.8, "military_spending_abs": 11_200_000_000, "manpower_active": 400_000, "manpower_reserve": 400_000,
        "nuclear_warheads": 0, "nuclear_status": 'non_nuclear', "government_type": "Unitary presidential republic", "stability_index": 62,
        "freedom_house_score": 58, "corruption_index": 34, "press_freedom": 108, "internet_penetration": 77.0, "urbanization": 58.0,
        "leader_name": "Prabowo Subianto", "leader_ideology": "Right-wing nationalism", "national_morale": 72, "war_weariness": 10,
        "region": "Asia", "sub_region": "South-eastern Asia"
    },
    {
        "iso3": "JPN", "iso2": "JP", "name": "Japan", "name_short": "Japan", "cow_code": 740, "un_m49": 392,
        "population": 124_000_000, "gdp_nominal": 4_200_000_000_000, "gdp_growth": 1.2, "gdp_per_capita": 33870,
        "inflation_rate": 2.8, "unemployment": 2.5, "gini": 33.4, "debt_to_gdp": 260.0, "forex_reserves": 1_270_000_000_000,
        "military_spending_pct_gdp": 1.2, "military_spending_abs": 50_400_000_000, "manpower_active": 247_000, "manpower_reserve": 56_000,
        "nuclear_warheads": 0, "nuclear_status": 'capable', "government_type": "Unitary parliamentary constitutional monarchy", "stability_index": 88,
        "freedom_house_score": 96, "corruption_index": 73, "press_freedom": 70, "internet_penetration": 94.0, "urbanization": 92.0,
        "leader_name": "Fumio Kishida", "leader_ideology": "Liberal conservatism", "national_morale": 68, "war_weariness": 25,
        "region": "Asia", "sub_region": "Eastern Asia"
    },
    {
        "iso3": "KOR", "iso2": "KR", "name": "Republic of Korea", "name_short": "South Korea", "cow_code": 732, "un_m49": 410,
        "population": 52_000_000, "gdp_nominal": 1_800_000_000_000, "gdp_growth": 1.4, "gdp_per_capita": 34600,
        "inflation_rate": 3.1, "unemployment": 2.8, "gini": 35.4, "debt_to_gdp": 54.0, "forex_reserves": 420_000_000_000,
        "military_spending_pct_gdp": 2.8, "military_spending_abs": 50_400_000_000, "manpower_active": 500_000, "manpower_reserve": 3_100_000,
        "nuclear_warheads": 0, "nuclear_status": 'capable', "government_type": "Unitary presidential republic", "stability_index": 70,
        "freedom_house_score": 81, "corruption_index": 63, "press_freedom": 47, "internet_penetration": 98.0, "urbanization": 81.5,
        "leader_name": "Yoon Suk Yeol", "leader_ideology": "Conservatism", "national_morale": 65, "war_weariness": 30,
        "region": "Asia", "sub_region": "Eastern Asia"
    },
    {
        "iso3": "SAU", "iso2": "SA", "name": "Kingdom of Saudi Arabia", "name_short": "Saudi Arabia", "cow_code": 670, "un_m49": 682,
        "population": 36_000_000, "gdp_nominal": 1_100_000_000_000, "gdp_growth": -0.5, "gdp_per_capita": 30560,
        "inflation_rate": 1.7, "unemployment": 4.9, "gini": 45.9, "debt_to_gdp": 28.0, "forex_reserves": 440_000_000_000,
        "military_spending_pct_gdp": 7.5, "military_spending_abs": 82_500_000_000, "manpower_active": 225_000, "manpower_reserve": 25_000,
        "nuclear_warheads": 0, "nuclear_status": 'capable', "government_type": "Absolute monarchy", "stability_index": 58,
        "freedom_house_score": 7, "corruption_index": 54, "press_freedom": 170, "internet_penetration": 98.0, "urbanization": 85.0,
        "leader_name": "Mohammed bin Salman", "leader_ideology": "Absolute monarchy", "national_morale": 78, "war_weariness": 15,
        "region": "Asia", "sub_region": "Western Asia"
    },
    # Oceania
    {
        "iso3": "AUS", "iso2": "AU", "name": "Commonwealth of Australia", "name_short": "Australia", "cow_code": 900, "un_m49": 36,
        "population": 26_000_000, "gdp_nominal": 1_700_000_000_000, "gdp_growth": 1.2, "gdp_per_capita": 65380,
        "inflation_rate": 4.1, "unemployment": 3.9, "gini": 34.3, "debt_to_gdp": 55.0, "forex_reserves": 80_000_000_000,
        "military_spending_pct_gdp": 2.1, "military_spending_abs": 35_700_000_000, "manpower_active": 60_000, "manpower_reserve": 30_000,
        "nuclear_warheads": 0, "nuclear_status": 'non_nuclear', "government_type": "Federal parliamentary constitutional monarchy", "stability_index": 82,
        "freedom_house_score": 95, "corruption_index": 75, "press_freedom": 39, "internet_penetration": 91.0, "urbanization": 86.0,
        "leader_name": "Anthony Albanese", "leader_ideology": "Social democracy", "national_morale": 72, "war_weariness": 20,
        "region": "Oceania", "sub_region": "Australia and New Zealand"
    },
    # Africa
    {
        "iso3": "ZAF", "iso2": "ZA", "name": "Republic of South Africa", "name_short": "South Africa", "cow_code": 560, "un_m49": 710,
        "population": 60_000_000, "gdp_nominal": 380_000_000_000, "gdp_growth": 0.5, "gdp_per_capita": 6330,
        "inflation_rate": 5.5, "unemployment": 32.9, "gini": 63.0, "debt_to_gdp": 72.0, "forex_reserves": 60_000_000_000,
        "military_spending_pct_gdp": 1.0, "military_spending_abs": 3_800_000_000, "manpower_active": 73_000, "manpower_reserve": 15_000,
        "nuclear_warheads": 0, "nuclear_status": 'non_nuclear', "government_type": "Unitary parliamentary republic", "stability_index": 45,
        "freedom_house_score": 73, "corruption_index": 43, "press_freedom": 38, "internet_penetration": 72.0, "urbanization": 68.0,
        "leader_name": "Cyril Ramaphosa", "leader_ideology": "Social democracy", "national_morale": 50, "war_weariness": 10,
        "region": "Africa", "sub_region": "Southern Africa"
    },
    # Supranational
    {
        "iso3": "EUR", "iso2": "EU", "name": "European Union", "name_short": "European Union", "cow_code": -1, "un_m49": -1,
        "population": 447_000_000, "gdp_nominal": 18_500_000_000_000, "gdp_growth": 0.5, "gdp_per_capita": 41400,
        "inflation_rate": 3.1, "unemployment": 6.0, "gini": 30.1, "debt_to_gdp": 83.5, "forex_reserves": 800_000_000_000,
        "military_spending_pct_gdp": 1.8, "military_spending_abs": 333_000_000_000, "manpower_active": 1_300_000, "manpower_reserve": 1_500_000,
        "nuclear_warheads": 290, "nuclear_status": 'armed', "government_type": "Supranational parliamentary democracy", "stability_index": 75,
        "freedom_house_score": 87, "corruption_index": 64, "press_freedom": 20, "internet_penetration": 90.0, "urbanization": 75.0,
        "leader_name": "Ursula von der Leyen", "leader_ideology": "Christian democracy", "national_morale": 65, "war_weariness": 50,
        "region": "Europe", "sub_region": "N/A"
    },
]

# --- Relationship Definitions ---

ALLIANCES = [
    {"name": "NATO", "type": "Military", "members": ["USA", "CAN", "GBR", "FRA", "DEU", "ITA", "TUR"]},
    {"name": "BRICS", "type": "Economic", "members": ["BRA", "RUS", "IND", "CHN", "ZAF"]},
    {"name": "SCO", "type": "Political-Military", "members": ["CHN", "RUS", "IND"]},
    {"name": "G20", "type": "Forum", "members": ["ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IND", "IDN", "ITA", "JPN", "KOR", "MEX", "RUS", "SAU", "ZAF", "TUR", "GBR", "USA", "EUR"]}
]

BORDERS = [
    ("USA", "CAN"), ("USA", "MEX"), ("FRA", "DEU"), ("FRA", "ITA"),
    ("DEU", "FRA"), ("DEU", "ITA"), # simplified
    ("RUS", "CHN"), ("IND", "CHN"), ("BRA", "ARG"),
]

COMMODITIES = [
    {
        "name": "Crude Oil",
        "producers": ["SAU", "RUS", "USA", "CAN", "BRA"],
        "consumers": ["CHN", "USA", "IND", "JPN", "DEU", "KOR", "EUR"]
    },
    {
        "name": "Semiconductors",
        "producers": ["KOR", "JPN", "USA", "CHN", "DEU"],
        "consumers": ["CHN", "USA", "EUR", "JPN", "KOR"]
    },
    {
        "name": "Wheat",
        "producers": ["CHN", "IND", "RUS", "USA", "FRA", "CAN", "AUS", "ARG"],
        "consumers": ["CHN", "IND", "EUR", "USA", "RUS", "IDN", "BRA"]
    },
    {
        "name": "Rare Earth Elements",
        "producers": ["CHN", "USA", "AUS"],
        "consumers": ["CHN", "USA", "JPN", "DEU", "KOR"]
    }
]

TRADES = [
    # North America
    {"from": "CAN", "to": "USA", "type": "Crude Oil", "volume": 3.8, "value": 100_000_000_000, "friction": 5},
    {"from": "MEX", "to": "USA", "type": "Automobiles", "volume": 1.2, "value": 90_000_000_000, "friction": 10},
    {"from": "USA", "to": "CAN", "type": "Machinery", "volume": 0.9, "value": 70_000_000_000, "friction": 5},
    {"from": "USA", "to": "MEX", "type": "Refined Petroleum", "volume": 1.5, "value": 60_000_000_000, "friction": 10},
    {"from": "USA", "to": "EUR", "type": "LNG", "volume": 1.0, "value": 50_000_000_000, "friction": 15},
    # Europe-Asia
    {"from": "CHN", "to": "DEU", "type": "Electronics", "volume": 2.5, "value": 150_000_000_000, "friction": 20},
    {"from": "DEU", "to": "CHN", "type": "Automobiles", "volume": 0.8, "value": 80_000_000_000, "friction": 20},
    {"from": "RUS", "to": "EUR", "type": "Natural Gas", "volume": 0.5, "value": 30_000_000_000, "friction": 80}, # High friction
    {"from": "RUS", "to": "CHN", "type": "Crude Oil", "volume": 2.1, "value": 85_000_000_000, "friction": 5},
    {"from": "RUS", "to": "IND", "type": "Crude Oil", "volume": 1.9, "value": 75_000_000_000, "friction": 10},
    {"from": "FRA", "to": "USA", "type": "Aerospace", "volume": 0.3, "value": 40_000_000_000, "friction": 10},
    # Asia-Pacific
    {"from": "SAU", "to": "CHN", "type": "Crude Oil", "volume": 2.0, "value": 80_000_000_000, "friction": 5},
    {"from": "SAU", "to": "JPN", "type": "Crude Oil", "volume": 1.4, "value": 55_000_000_000, "friction": 5},
    {"from": "SAU", "to": "KOR", "type": "Crude Oil", "volume": 1.1, "value": 45_000_000_000, "friction": 5},
    {"from": "AUS", "to": "CHN", "type": "Iron Ore", "volume": 900.0, "value": 100_000_000_000, "friction": 25},
    {"from": "KOR", "to": "CHN", "type": "Semiconductors", "volume": 0.1, "value": 60_000_000_000, "friction": 15},
    {"from": "KOR", "to": "USA", "type": "Semiconductors", "volume": 0.08, "value": 50_000_000_000, "friction": 10},
    {"from": "JPN", "to": "USA", "type": "Automobiles", "volume": 1.5, "value": 55_000_000_000, "friction": 10},
    {"from": "JPN", "to": "CHN", "type": "Machinery", "volume": 1.0, "value": 45_000_000_000, "friction": 15},
    {"from": "IND", "to": "USA", "type": "Pharmaceuticals", "volume": 0.5, "value": 30_000_000_000, "friction": 10},
    {"from": "CHN", "to": "IND", "type": "Active Pharma Ingredients", "volume": 0.4, "value": 25_000_000_000, "friction": 35},
    # South America
    {"from": "BRA", "to": "CHN", "type": "Soybeans", "volume": 80.0, "value": 40_000_000_000, "friction": 10},
    {"from": "BRA", "to": "USA", "type": "Crude Oil", "volume": 0.5, "value": 15_000_000_000, "friction": 15},
    {"from": "ARG", "to": "BRA", "type": "Automotive Parts", "volume": 0.7, "value": 10_000_000_000, "friction": 10},
    # Other
    {"from": "ZAF", "to": "CHN", "type": "Precious Metals", "volume": 0.2, "value": 20_000_000_000, "friction": 10},
    {"from": "TUR", "to": "DEU", "type": "Textiles", "volume": 1.0, "value": 15_000_000_000, "friction": 20},
    {"from": "GBR", "to": "USA", "type": "Financial Services", "volume": 0, "value": 50_000_000_000, "friction": 5},
    {"from": "IDN", "to": "CHN", "type": "Coal", "volume": 200.0, "value": 25_000_000_000, "friction": 10},
    {"from": "CHN", "to": "RUS", "type": "Drones & Vehicles", "volume": 0.3, "value": 10_000_000_000, "friction": 5},
    {"from": "ITA", "to": "DEU", "type": "Luxury Goods", "volume": 0.2, "value": 20_000_000_000, "friction": 5}
]

FACTIONS = {
    "RUS": [{"name": "Siloviki", "ideology": "Hardline Security State", "influence": 80, "power": 85},
            {"name": "Economic Technocrats", "ideology": "State Capitalism", "influence": 50, "power": 60},
            {"name": "Ultranationalists", "ideology": "Imperial Expansionism", "influence": 70, "power": 50}],
    "IND": [{"name": "BJP Core", "ideology": "Hindu Nationalism", "influence": 90, "power": 90},
            {"name": "Congress Loyalists", "ideology": "Secular Centrism", "influence": 40, "power": 30},
            {"name": "Regional Parties Bloc", "ideology": "Federalism", "influence": 60, "power": 55}],
    "DEU": [{"name": "Green Industrialists", "ideology": "Eco-Capitalism", "influence": 75, "power": 70},
            {"name": "Social Democrats", "ideology": "Welfare State", "influence": 65, "power": 75},
            {"name": "Fiscal Conservatives", "ideology": "Austerity", "influence": 60, "power": 60}],
    "JPN": [{"name": "LDP Establishment", "ideology": "Conservative Nationalism", "influence": 85, "power": 90},
            {"name": "Constitutional Pacifists", "ideology": "Anti-militarism", "influence": 50, "power": 40}],
    "BRA": [{"name": "Lulistas", "ideology": "Developmentalism", "influence": 70, "power": 80},
            {"name": "Agribusiness Lobby", "ideology": "Free Market Export", "influence": 80, "power": 70},
            {"name": "Bolsonaristas", "ideology": "Right-wing Populism", "influence": 60, "power": 50}],
}

# --- Main Functions ---

def clear_mock_data(tx):
    """Deletes all nodes and relationships created by this script."""
    logging.info(f"Clearing old mock data with tag: '{DATA_QUALITY_TAG}'")
    query = f"""
    MATCH (n) WHERE n.data_quality = $tag
    DETACH DELETE n
    """
    result = tx.run(query, tag=DATA_QUALITY_TAG)
    summary = result.consume()
    logging.info(f"Deleted {summary.counters.nodes_deleted} nodes and {summary.counters.relationships_deleted} relationships.")

def load_data(driver):
    """Main function to load all mock data into the Neo4j database."""
    with driver.session(database="neo4j") as session:
        # Clear previous mock data in a single transaction
        session.execute_write(clear_mock_data)

        # Create Nations
        logging.info(f"Loading {len(NATIONS_DATA)} nations...")
        session.execute_write(
            lambda tx: tx.run("""
            UNWIND $nations as nation_data
            MERGE (n:Nation {iso3: nation_data.iso3})
            SET n = nation_data, n.data_quality = $tag
            """, nations=NATIONS_DATA, tag=DATA_QUALITY_TAG)
        )

        # Create Alliances
        logging.info(f"Loading {len(ALLIANCES)} alliances and memberships...")
        session.execute_write(
            lambda tx: tx.run("""
            UNWIND $alliances as alliance_data
            MERGE (a:Alliance {name: alliance_data.name})
            SET a.type = alliance_data.type, a.data_quality = $tag
            WITH a, alliance_data.members as member_list
            UNWIND member_list as member_iso3
            MATCH (n:Nation {iso3: member_iso3})
            MERGE (n)-[:MEMBER_OF]->(a)
            """, alliances=ALLIANCES, tag=DATA_QUALITY_TAG)
        )

        # Create Commodities and relationships
        logging.info(f"Loading {len(COMMODITIES)} commodities and relationships...")
        session.execute_write(
            lambda tx: tx.run("""
            UNWIND $commodities as commodity_data
            MERGE (c:Commodity {name: commodity_data.name})
            SET c.data_quality = $tag

            WITH c, commodity_data
            UNWIND commodity_data.producers as producer_iso3
            MATCH (n:Nation {iso3: producer_iso3})
            MERGE (n)-[:PRODUCES]->(c)

            WITH c, commodity_data
            UNWIND commodity_data.consumers as consumer_iso3
            MATCH (n:Nation {iso3: consumer_iso3})
            MERGE (n)-[:CONSUMES]->(c)
            """, commodities=COMMODITIES, tag=DATA_QUALITY_TAG)
        )

        # Create Border relationships
        logging.info(f"Loading {len(BORDERS)} border relationships...")
        session.execute_write(
            lambda tx: tx.run("""
            UNWIND $borders as border_pair
            MATCH (n1:Nation {iso3: border_pair[0]})
            MATCH (n2:Nation {iso3: border_pair[1]})
            MERGE (n1)-[:BORDERS]-(n2)
            """, borders=BORDERS)
        )

        # Create Trade relationships
        logging.info(f"Loading {len(TRADES)} trade relationships...")
        session.execute_write(
            lambda tx: tx.run("""
            UNWIND $trades as trade_data
            MATCH (exporter:Nation {iso3: trade_data.from})
            MATCH (importer:Nation {iso3: trade_data.to})
            MERGE (exporter)-[r:TRADES_WITH]->(importer)
            SET r.commodity_type = trade_data.type,
                r.volume_metric_tons_millions = trade_data.volume,
                r.value_usd_billions = trade_data.value,
                r.friction = trade_data.friction,
                r.data_quality = $tag
            """, trades=TRADES, tag=DATA_QUALITY_TAG)
        )

        # Create Factions
        logging.info(f"Loading factions for {len(FACTIONS)} nations...")
        session.execute_write(
            lambda tx: tx.run("""
            UNWIND keys($factionMap) as country_iso3
            MATCH (n:Nation {iso3: country_iso3})
            UNWIND $factionMap[country_iso3] as faction_data
            CREATE (f:DomesticFaction {name: faction_data.name})
            SET f += faction_data, f.data_quality = $tag
            MERGE (n)-[:HAS_FACTION]->(f)
            """, factionMap=FACTIONS, tag=DATA_QUALITY_TAG)
        )

def main():
    """Establishes connection and orchestrates the data loading process."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        logging.info("Successfully connected to Neo4j.")
        
        load_data(driver)
        
        logging.info("Script finished successfully. All mock data loaded.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        if 'driver' in locals() and driver:
            driver.close()
            logging.info("Neo4j connection closed.")

if __name__ == "__main__":
    main()
