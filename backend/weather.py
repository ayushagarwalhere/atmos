"""Weather input definitions and sourced, qualitative scenario interpretation."""
from datetime import datetime

WEATHER_FIELDS = {
    'rain_mm': ('rain', 0, 200),
    'cloud_cover_pct': ('cloud_cover', 0, 100),
    'humidity_pct': ('relative_humidity_2m', 0, 100),
    'temperature_c': ('temperature_2m', -90, 65),
    'boundary_layer_height': ('boundary_layer_height', 0, 10000),
}
BURNING_TYPES = {
    'unspecified': 'Satellite detections do not identify the fuel or confirm crop burning.',
    'crop_residue': 'Crop residue burning can emit fine particles and gases. This is a user-selected source assumption, not satellite-confirmed attribution.',
    'wildfire': 'Vegetation fires emit particles and gases; fuel moisture, combustion phase and plume height affect their transport.',
    'waste': 'Waste burning can release particles and toxic gases. PM2.5 alone does not describe its full pollutant mixture.',
}
SOURCES = [
    {'title': 'Open-Meteo weather variables', 'url': 'https://open-meteo.com/en/docs'},
    {'title': 'EPA: smoke transport and deposition', 'url': 'https://www.epa.gov/sciencematters/tracking-smoke-models-protect-public-health'},
    {'title': 'EPA: what is in smoke', 'url': 'https://www.epa.gov/wildfire-smoke-course/wildfire-smoke-complex-mixture'},
]

def current_weather(city_id, at, winds, overrides=None):
    samples = [row for row in winds if row.get('city_id') == city_id and 0 <= (at-datetime.fromisoformat(row['time'])).total_seconds() <= 3600]
    row = max(samples, key=lambda item: item['time']) if samples else {}
    observed = {name: row.get(name) for name in WEATHER_FIELDS}
    observed.update(speed_kmh=row.get('speed_kmh'), direction_deg=row.get('direction_deg'))
    effective = dict(observed)
    mapping = {'speed': 'speed_kmh', 'direction': 'direction_deg', **{name: name for name in WEATHER_FIELDS}}
    for key, value in (overrides or {}).items():
        if key in mapping and value is not None:
            effective[mapping[key]] = value
    return {'observed': observed, 'effective': effective, 'source': row.get('source', 'Weather unavailable'),
        'time': row.get('time'), 'missing': [name for name in WEATHER_FIELDS if effective[name] is None]}

def interpret_weather(weather, multiplier=1, smoke_factor=1, burning='unspecified'):
    values = weather['effective']
    speed, rain, cloud = values.get('speed_kmh'), values.get('rain_mm'), values.get('cloud_cover_pct')
    notes = [
        {'factor': 'Wind', 'text': 'Wind direction determines the downwind path. Faster wind can carry smoke farther while dispersing it; city concentrations need not rise with speed.' if speed is None or speed > 3 else 'Calm wind limits travel and may let pollution accumulate near sources. The simple drift model cannot resolve local stagnation.'},
        {'factor': 'Rain', 'text': 'Rain can remove airborne particles through wet deposition. Removal depends on particle size, rainfall and plume overlap; this app learns an association from history.' if rain is not None and rain > 0 else 'No rain is assumed at this input hour, so rainfall removal is not represented by this input.' if rain == 0 else 'Rain data is missing; a dry hour is not assumed.'},
        {'factor': 'Clouds', 'text': 'Clouds influence sunlight, chemistry and atmospheric mixing, and can obscure satellite fires. Cloud cover alone has no fixed PM2.5 effect; its forecast response is learned from data.'},
        {'factor': 'Burning', 'text': BURNING_TYPES[burning] + f' Fire activity is {multiplier:g}×; the assumed smoke-emission proxy is {smoke_factor:g}× per detection. These are scenario assumptions.'},
    ]
    return {'weather': weather, 'notes': notes, 'references': SOURCES,
        'method': 'Weather overrides change issue-hour model features. Numerical differences are learned associations, not measured causal effects. Wind paths do not simulate wet deposition or plume chemistry.'}
