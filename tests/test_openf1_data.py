import unittest
from src.data import exclusion_reasons
from src.openf1_data import normalize_laps


class OpenF1Tests(unittest.TestCase):
    def test_normalization_preserves_unknown_quality_and_used_tyres(self):
        laps = [{'driver_number': 1, 'lap_number': 5, 'lap_duration': 96.0,
                 'is_pit_out_lap': False, 'date_start': '2024-03-02T15:00:00Z'}]
        stints = [{'lap_start': 4, 'lap_end': 8, 'stint_number': 2,
                   'compound': 'HARD', 'tyre_age_at_start': 3}]
        rows = normalize_laps(laps, stints, [{'lap_number': 5}], 'VER')
        self.assertEqual(rows[0]['tyre_life_laps'], 5)
        self.assertIsNone(rows[0]['is_accurate'])
        reasons = exclusion_reasons(rows[0])
        self.assertIn('pit_in_lap', reasons)
        self.assertIn('not_flagged_accurate', reasons)

    def test_missing_lap_duration_is_never_imputed(self):
        rows = normalize_laps([{'driver_number': 1, 'lap_number': 1, 'lap_duration': None}], [], [], 'VER')
        self.assertIsNone(rows[0]['lap_time_s'])
        self.assertIn('missing_or_invalid_lap_time_s', exclusion_reasons(rows[0]))
