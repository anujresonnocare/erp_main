from odoo import api, SUPERUSER_ID


GST_STATES = [
    ('Andaman and Nicobar Islands', 'AN', None, None),
    ('Andhra Pradesh', 'AP', None, None),
    ('Andhra Pradesh (New)', 'AD', None, None),
    ('Arunachal Pradesh', 'AR', None, None),
    ('Assam', 'AS', None, None),
    ('Bihar', 'BH', None, None),
    ('Chandigarh', 'CH', None, None),
    ('Chattisgarh', 'CT', None, None),
    ('Dadra and Nagar Haveli', 'DN', None, None),
    ('Daman and Diu', 'DD', None, None),
    ('Delhi', 'DL', '07AAPCR0087G1Z5', 'Building No./Flat No.: D-3/14\nRoad/Street: VASANT VIHAR CLUB ROAD\nCity/Town/Village: New Delhi\nDistrict: New Delhi\nState: Delhi\nPIN Code: 110057'),
    ('Goa', 'GA', None, None),
    ('Gujarat', 'GJ', None, None),
    ('Haryana', 'HR', '06AAPCR0087G1Z7', 'Floor No.: Floor No. 01\nBuilding No./Flat No.: 0-144\nName Of Premises/Building: DLF Shopping Mall\nRoad/Street: Arjun Marg\nLocality/Sub Locality: Sector 26A\nCity/Town/Village: Gurugram\nDistrict: Gurugram\nState - Haryana\nPIN Code - 122002'),
    ('Himachal Pradesh', 'HP', None, None),
    ('Jammu and Kashmir', 'JK', None, None),
    ('Jharkhand', 'JH', None, None),
    ('Karnataka', 'KA', '29AAPCR0087G1ZZ', 'Building No./Flat No.: Site No. 499\nRoad/Street: EAST END MAIN ROAD, 9TH BLOCK, JAYANAGAR DIVISION\nNO.60\nCity/Town/Village: Bengaluru\nDistrict: Bengaluru Urban\nState: Karnataka\nPIN Code: 560076'),
    ('Kerala', 'KL', None, None),
    ('Lakshadweep Islands', 'LD', None, None),
    ('Madhya Pradesh', 'MP', None, None),
    ('Maharashtra', 'MH', None, None),
    ('Manipur', 'MN', None, None),
    ('Meghalaya', 'ME', None, None),
    ('Mizoram', 'MI', None, None),
    ('Nagaland', 'NL', None, None),
    ('Odisha', 'OR', None, None),
    ('Pondicherry', 'PY', None, None),
    ('Punjab', 'PB', '03AAPCR0087G1ZD', 'Building No.: 963 GROUND FLOOR\nRoad/Street: BRS Nagar Main Road\nNearby Landmark: BRS Nagar Market\nCity/Town/Village: Ludhiana\nDistrict: Ludhiana\nState: Punjab\nPIN Code: 141012'),
    ('Rajasthan', 'RJ', None, None),
    ('Sikkim', 'SK', None, None),
    ('Tamil Nadu', 'TN', None, None),
    ('Telangana', 'TS', None, None),
    ('Tripura', 'TR', None, None),
    ('Uttar Pradesh', 'UP', None, None),
    ('Uttarakhand', 'UT', None, None),
    ('West Bengal', 'WB', None, None),
]

ALIASES = {
    'Chattisgarh': ['Chattisgarh', 'Chhattisgarh'],
    'Pondicherry': ['Pondicherry', 'Puducherry'],
    'Dadra and Nagar Haveli': ['Dadra and Nagar Haveli'],
    'Daman and Diu': ['Daman and Diu'],
}


def post_init_hook(env):
    State = env['res.country.state'].with_user(SUPERUSER_ID)
    india = env['res.country'].search([('code', '=', 'IN')], limit=1)
    if not india:
        return

    for name, code, gstin, hq in GST_STATES:
        names = ALIASES.get(name, [name])
        # IMPORTANT: Odoo requires state.code to be unique per country.
        # First match the existing Odoo state by its code, then by name/alias.
        # This avoids creating duplicates such as Chattisgarh/Chhattisgarh or
        # Pondicherry/Puducherry when the standard Odoo database already has them.
        state = State.search([
            ('country_id', '=', india.id),
            ('code', '=', code),
        ], limit=1)
        if not state:
            state = State.search([
                ('country_id', '=', india.id),
                ('name', 'in', names),
            ], limit=1)

        # Andhra Pradesh (New) represents GST/TIN code 37 and may not exist
        # in a standard Odoo database. If it does not exist, create it using
        # the GST state code as its Odoo code (AD), provided that code is free.
        if not state:
            state = State.create({
                'name': name,
                'code': code,
                'country_id': india.id,
            })

        state.write({
            'code': code,
            'name': name,
            'gstin': gstin or False,
            'gst_state_hq': hq or False,
        })
