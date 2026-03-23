import json
import re

def update_crosswalk_with_vdem(crosswalk_file, vdem_file):
    with open(crosswalk_file, 'r') as f:
        crosswalk_data = json.load(f)

    with open(vdem_file, 'r') as f:
        vdem_text = f.read()

    # This is a bit brittle, but we are looking for the table at the end
    # of the document.
    table_section = vdem_text.split("| Afghanistan")[1]

    vdem_map = {}
    for line in table_section.split('\n'):
        # using regex to find all the elements in the | separated table
        matches = re.findall(r'\|([^|]+)', line)
        if len(matches) >= 3:
            country_name = matches[0].strip()
            vdem_id = matches[1].strip()
            # there are cases where the vdem id is in the next column
            if not vdem_id.isnumeric() and len(matches) >= 4:
              vdem_id = matches[2].strip()

            if vdem_id.isnumeric():
              vdem_map[country_name] = int(vdem_id)


    for country in crosswalk_data:
        country_name = country.get('name_en')
        if country_name in vdem_map:
            country['vdem_code'] = vdem_map[country_name]
        # try short name
        else:
          country_name = country.get('name_short')
          if country_name in vdem_map:
            country['vdem_code'] = vdem_map[country_name]


    # a few manual fixes for names that don't match
    # South Korea
    for country in crosswalk_data:
        if country['iso3'] == 'KOR':
            country['vdem_code'] = 42
            break
    # North Korea
    for country in crosswalk_data:
        if country['iso3'] == 'PRK':
            country['vdem_code'] = 41
            break
    # Kosovo
    for country in crosswalk_data:
        if country['iso3'] == 'XKX':
            country['vdem_code'] = 43
            break
    # Taiwan
    for country in crosswalk_data:
        if country['iso3'] == 'TWN':
            country['vdem_code'] = 48
            break

    with open(crosswalk_file, 'w') as f:
        json.dump(crosswalk_data, f, indent=4)


if __name__ == '__main__':
    crosswalk_file = 'data/id_crosswalk.json'
    vdem_file = 'vdem.txt'
    update_crosswalk_with_vdem(crosswalk_file, vdem_file)
    print("Crosswalk file updated with V-Dem codes.")
