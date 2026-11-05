import unittest
from src.data import audit_records, exclusion_reasons


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.row = {'lap_number': '4.0', 'lap_time_s': '95.1', 'tyre_life_laps': '4',
                    'stint': '1', 'compound': 'SOFT', 'pit_in_time_s': '', 'pit_out_time_s': '',
                    'is_accurate': 'True', 'fastf1_generated': 'False', 'deleted': 'False',
                    'track_status': '1'}

    def test_ordinary_lap_is_eligible(self):
        self.assertEqual(exclusion_reasons(self.row), [])

    def test_pit_laps_remain_in_dataset_but_are_excluded_from_normal_fit(self):
        row = dict(self.row, pit_in_time_s='500', is_accurate='False')
        annotated, audit = audit_records([self.row, row])
        self.assertEqual(len(annotated), 2)
        self.assertFalse(annotated[1]['calibration_eligible'])
        self.assertIn('pit_in_lap', annotated[1]['exclusion_reasons'])
        self.assertEqual(audit['eligible_normal_laps'], 1)

    def test_generated_missing_and_flagged_laps_cannot_enter_normal_fit(self):
        for fields in [{'fastf1_generated': 'True'}, {'lap_time_s': ''}, {'track_status': '14'},
                       {'compound': 'UNKNOWN'}, {'deleted': 'True'}, {'lap_number': '1.0'}]:
            with self.subTest(fields=fields):
                self.assertTrue(exclusion_reasons(dict(self.row, **fields)))
