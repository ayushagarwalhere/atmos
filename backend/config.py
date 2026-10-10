import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DATA_DIR = Path(os.getenv('ATMOS_DATA_DIR', ROOT / 'data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CITIES = [
    {'id': 'delhi', 'name': 'Delhi', 'lat': 28.6139, 'lon': 77.2090},
    {'id': 'chandigarh', 'name': 'Chandigarh', 'lat': 30.7333, 'lon': 76.7794},
    {'id': 'ludhiana', 'name': 'Ludhiana', 'lat': 30.9010, 'lon': 75.8573},
    {'id': 'lucknow', 'name': 'Lucknow', 'lat': 26.8467, 'lon': 80.9462},
]
LIMITS = [
    'Satellite hotspots are detections, not confirmed crop-residue fires; cloud cover and overpass timing miss fires.',
    'Regional bounding-box selection can include neighbouring areas. Crop attribution needs land-use validation.',
    'Hourly 10 m wind drift ignores vertical mixing, chemistry, deposition and fine-scale terrain. It is not HYSPLIT.',
    'PM2.5 has many sources. An arrival/rise association does not establish the fire contribution.',
    'PM2.5-only Indian sub-index is not the overall official AQI; sufficient 24-hour coverage is required.',
]
