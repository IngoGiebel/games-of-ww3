import json
import re

def update_crosswalk_with_acled(crosswalk_file, acled_file):
    with open(crosswalk_file, 'r') as f:
        crosswalk_data = json.load(f)

    with open(acled_file, 'r') as f:
        acled_text = f.read()

    # The table is the first part of the markdown
    table_section = acled_text.split("Share on")[0]

    acled_map = {}
    for line in table_section.split('\n'):
        matches = re.findall(r'|([^|]+)', line)
        if len(matches) >= 3:
            country_name = matches[0].strip()
            # This is not a perfect mapping, but it's a start.
            # I will have to do some manual mapping.
            acled_map[country_name] = country_name

    for country in crosswalk_data:
        country_name = country.get('name_en')
        if country_name in acled_map:
            country['acled_name'] = acled_map[country_name]
        else:
          # try short name
          country_name = country.get('name_short')
          if country_name in acled_map:
            country['acled_name'] = acled_map[country_name]


    # Manual fixes
    acled_manual_map = {
        "Bolivia, Plurinational State of": "Bolivia",
        "Brunei Darussalam": "Brunei",
        "Cabo Verde": "Cape Verde",
        "Congo, Democratic Republic of the": "Democratic Republic of Congo",
        "Congo": "Republic of Congo",
        "Côte d'Ivoire": "Ivory Coast",
        "Czechia": "Czech Republic",
        "Eswatini (Swaziland)": "eSwatini",
        "Iran, Islamic Republic of": "Iran",
        "Korea, Republic of": "South Korea",
        "Lao People's Democratic Republic": "Laos",
        "Micronesia, Federated States of": "Micronesia",
        "Moldova, Republic of": "Moldova",
        "Netherlands, Kingdom of the": "Netherlands",
        "Russian Federation": "Russia",
        "Syrian Arab Republic": "Syria",
        "Tanzania, United Republic of": "Tanzania",
        "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
        "United States of America": "United States",
        "Venezuela, Bolivarian Republic of": "Venezuela",
        "Viet Nam": "Vietnam"
    }

    for country in crosswalk_data:
        if country['name_en'] in acled_manual_map:
            country['acled_name'] = acled_manual_map[country['name_en']]
        if country.get('name_short') in acled_manual_map:
            country['acled_name'] = acled_manual_map[country['name_short']]


    with open(crosswalk_file, 'w') as f:
        json.dump(crosswalk_data, f, indent=4)


if __name__ == '__main__':
    crosswalk_file = 'data/id_crosswalk.json'
    acled_file = 'acled_countries.md'
    update_crosswalk_with_acled(crosswalk_file, acled_file)
    print("Crosswalk file updated with ACLED names.")
