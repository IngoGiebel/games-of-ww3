import json

def load_world_bank_data(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    country_data = {}
    for entry in data[1]:
        iso3 = entry.get('countryiso3code')
        if iso3:
            country_data[iso3] = {
                'wb_code': iso3,
                'name_short': entry.get('country', {}).get('value')
            }
    return country_data

def create_base_crosswalk(input_file, output_file, wb_data):
    with open(input_file, 'r') as f:
        data = json.load(f)

    crosswalk = []
    for country in data:
        # We need to filter out territories that aren't sovereign nations
        if country.get('region'):  # A simple filter for now
            iso3 = country.get('alpha-3')
            wb_info = wb_data.get(iso3, {})
            crosswalk.append({
                'iso3': iso3,
                'iso2': country.get('alpha-2'),
                'un_m49': country.get('country-code'),
                'name_en': country.get('name'),
                'name_short': wb_info.get('name_short'),
                'cow_code': None, # To be filled in
                'wb_code': wb_info.get('wb_code'),
                'vdem_code': None, # To be filled in
                'acled_name': None, # To be filled in
            })

    # Add special cases
    crosswalk.extend([
        {
            'iso3': 'TWN',
            'iso2': 'TW',
            'un_m49': '158',
            'name_en': 'Taiwan, Province of China',
            'name_short': 'Taiwan',
            'cow_code': None,
            'wb_code': None,
            'vdem_code': None,
            'acled_name': None,
        },
        {
            'iso3': 'XKX',
            'iso2': 'XK',
            'un_m49': None, # Kosovo does not have an M49 code
            'name_en': 'Kosovo',
            'name_short': 'Kosovo',
            'cow_code': None,
            'wb_code': 'XKX', # World bank uses XKX
            'vdem_code': None,
            'acled_name': None,
        },
        {
            'iso3': 'PSE',
            'iso2': 'PS',
            'un_m49': '275',
            'name_en': 'Palestine, State of',
            'name_short': 'Palestine',
            'cow_code': None,
            'wb_code': 'PSE',
            'vdem_code': None,
            'acled_name': None,
        },
        {
            'iso3': 'ESH',
            'iso2': 'EH',
            'un_m49': '732',
            'name_en': 'Western Sahara',
            'name_short': 'Western Sahara',
            'cow_code': None,
            'wb_code': None,
            'vdem_code': None,
            'acled_name': None,
        }
    ])


    # Sort by iso3
    crosswalk.sort(key=lambda x: x['iso3'] if x['iso3'] else "")

    with open(output_file, 'w') as f:
        json.dump(crosswalk, f, indent=4)

if __name__ == '__main__':
    # The path to the scraped file needs to be updated
    input_file = '/home/uranus/.gemini/tmp/games-of-ww3/tool-outputs/session-0b4efc43-55f4-4f66-9a50-80753ed5b2ee/scraped_data.json'
    output_file = 'data/id_crosswalk.json'
    world_bank_file = '/home/uranus/.gemini/tmp/games-of-ww3/tool-outputs/session-0b4efc43-55f4-4f66-9a50-80753ed5b2ee/world_bank_data.json'

    # I need to get the actual content from the file
    # and save it as a proper JSON file first
    with open('/home/uranus/.gemini/tmp/games-of-ww3/tool-outputs/session-0b4efc43-55f4-4f66-9a50-80753ed5b2ee/mcp_firecrawl_firecrawl_scrape_1774272736686_0.txt', 'r') as f:
      content = f.read()
      # it's not a valid json, it's a markdown file with the json in it
      # I need to extract the json from the markdown
      json_content = content[content.find('['):content.rfind(']')+1]


    with open(input_file, 'w') as f:
        f.write(json_content)

    wb_data = load_world_bank_data(world_bank_file)
    create_base_crosswalk(input_file, output_file, wb_data)
    print(f"Base crosswalk created at {output_file}")

