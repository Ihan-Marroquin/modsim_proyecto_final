"""Genera una reproducción local con las salidas del simulador determinista."""
import html
import json
import math
from pathlib import Path

from .domain import strategy_from_dict
from .model import simulate_bahrain_case


def project_track(geojson: dict) -> list[list[float]]:
    """Proyección plana local del circuito, en metros aproximados."""
    coordinates = geojson['features'][0]['geometry']['coordinates']
    lon0, lat0 = coordinates[0]
    cos_lat = math.cos(math.radians(lat0))
    return [[round((lon - lon0) * cos_lat * 111_195, 3),
             round((lat0 - lat) * 111_195, 3)] for lon, lat in coordinates]


def replay_laps(report: dict) -> list[dict]:
    stops = set(report['strategy']['stops_after_lap'])
    return [{
        'lap': row['lap'],
        'tyre': row['compound'],
        'age': row['tyre_age_end_laps'],
        'pit': row['additional_pit_loss_s'],
        'stop': row['lap'] in stops,
        'end': round(row['cumulative_s'], 7),
    } for row in report['laps']]


def build_replay(root: Path, output_dir: Path) -> Path:
    assets = root / 'presentation' / 'replay'
    candidate_path = root / 'docs' / 'evidence' / 'optimization' / 'candidate.json'
    candidate = strategy_from_dict(json.loads(candidate_path.read_text(encoding='utf-8')))
    track = project_track(json.loads((assets / 'bh-2002.geojson').read_text(encoding='utf-8')))
    case = json.loads((root / 'configs' / 'case_bahrain_2024.json').read_text(encoding='utf-8'))
    scenes = {}
    for scene, multiplier in (('base', 1.0), ('wear', 1.2)):
        scenes[scene] = {
            role: replay_laps(simulate_bahrain_case(root_dir=root, degradation_multiplier=multiplier,
                                                  strategy=strategy))
            for role, strategy in (('historical', None), ('candidate', candidate))
        }
    data = {'track': track, 'scenes': scenes, 'official_time_s': case['official_winner_time_s']}
    packed = json.dumps(data, separators=(',', ':')).replace('<', '\\u003c')
    license_text = (assets / 'LICENSE-MAP.txt').read_text(encoding='utf-8')
    template = (assets / 'template.html').read_text(encoding='utf-8')
    output_dir.mkdir(parents=True, exist_ok=True)
    page = (output_dir / 'bahrein.html').resolve()
    page.write_text(template.replace('__RACE_DATA__', packed)
                            .replace('__MAP_LICENSE__', html.escape(license_text)), encoding='utf-8')
    return page
