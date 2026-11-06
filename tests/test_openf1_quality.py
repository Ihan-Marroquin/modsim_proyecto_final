"""Pruebas del filtro propio de OpenF1 con mensajes de control de carrera construidos a mano.

Son fixtures etiquetados: prueban las reglas, no validan el caso real.
"""
import unittest
from datetime import datetime, timedelta, timezone
from src.openf1_data import normalize_laps
from src.openf1_quality import apply_openf1_quality_filter

START = datetime(2024, 3, 2, 15, 0, 0, tzinfo=timezone.utc)
LAP_S = 100.0


def at(lap: int, offset_s: float) -> str:
    """Instante dentro de la vuelta `lap` (1 = primera), con vueltas de 100 s."""
    return (START + timedelta(seconds=(lap - 1) * LAP_S + offset_s)).isoformat()


def message(lap, offset, text, flag=None, scope=None, sector=None, category='Other', driver=None):
    return {'date': at(lap, offset), 'lap_number': lap, 'message': text, 'flag': flag,
            'scope': scope, 'sector': sector, 'category': category, 'driver_number': driver}


class OpenF1QualityFilterTests(unittest.TestCase):
    def setUp(self):
        self.laps = [{'driver_number': 1, 'lap_number': n, 'lap_duration': LAP_S,
                      'is_pit_out_lap': n == 6, 'date_start': at(n, 0)} for n in range(1, 11)]
        self.stints = [{'lap_start': 1, 'lap_end': 5, 'stint_number': 1, 'compound': 'SOFT', 'tyre_age_at_start': 3},
                       {'lap_start': 6, 'lap_end': 10, 'stint_number': 2, 'compound': 'HARD', 'tyre_age_at_start': 0}]
        self.records = normalize_laps(self.laps, self.stints, [{'lap_number': 5}], 'VER')

    def run_filter(self, race_control=(), weather=()):
        return apply_openf1_quality_filter(self.records, self.laps, list(race_control), list(weather), 1)

    def by_lap(self, annotated):
        return {row['lap_number']: row for row in annotated}

    def test_clean_race_keeps_normal_laps_and_never_drops_rows(self):
        annotated, table, report = self.run_filter()
        self.assertEqual(len(annotated), 10)
        self.assertEqual(len(table), 10)
        rows = self.by_lap(annotated)
        self.assertEqual(rows[1]['exclusion_reasons'], 'first_lap')
        self.assertEqual(rows[5]['exclusion_reasons'], 'pit_in_lap')
        self.assertEqual(rows[6]['exclusion_reasons'], 'pit_out_lap')
        self.assertEqual(report['eligible_normal_laps'], 7)
        # Las banderas de FastF1 siguen desconocidas: no se rellenan con True.
        self.assertIsNone(rows[3]['is_accurate'])
        self.assertIsNone(rows[3]['deleted'])

    def test_deleted_time_of_target_driver_excludes_only_that_lap(self):
        rc = [message(4, 50, 'CAR 1 (VER) TIME 1:40.000 DELETED - TRACK LIMITS AT TURN 4 LAP 3 18:05:00'),
              message(4, 60, 'CAR 44 (HAM) TIME 1:40.000 DELETED - TRACK LIMITS AT TURN 4 LAP 7 18:05:00')]
        annotated, _, report = self.run_filter(rc)
        rows = self.by_lap(annotated)
        self.assertIn('time_deleted_race_control', rows[3]['exclusion_reasons'])
        self.assertTrue(rows[3]['track_limits_deleted_rc'])
        self.assertTrue(rows[7]['calibration_eligible'])
        self.assertTrue(report['deleted_laps'][3]['time_matches_lap_duration'])

    def test_next_lap_deletion_and_time_mismatch_are_resolved_and_warned(self):
        rc = [message(5, 10, 'CAR 1 (VER) TIME 1:40.000 DELETED - TRACK LIMITS AT TURN 15 LAP 3 18:08:35'),
              message(5, 11, 'CAR 1 (VER) TIME 1:39.000 DELETED - TRACK LIMITS AT TURN 15 (NEXT LAP)')]
        annotated, _, _ = self.run_filter(rc)
        rows = self.by_lap(annotated)
        self.assertIn('time_deleted_race_control', rows[4]['exclusion_reasons'])
        self.assertIn('deleted_time_mismatch', rows[4]['quality_warnings'])

    def test_safety_car_excludes_laps_until_track_green_and_pit_exit_green_does_not_close_it(self):
        rc = [message(3, 50, 'SAFETY CAR DEPLOYED', category='SafetyCar'),
              message(4, 50, 'GREEN LIGHT - PIT EXIT OPEN', flag='GREEN', scope='Track', category='Flag'),
              message(7, 20, 'TRACK CLEAR', flag='GREEN', scope='Track', category='Flag')]
        annotated, _, _ = self.run_filter(rc)
        rows = self.by_lap(annotated)
        for lap in (3, 4, 7):
            self.assertIn('track_neutralization', rows[lap]['exclusion_reasons'], lap)
        self.assertNotIn('track_neutralization', rows[2]['exclusion_reasons'])
        self.assertNotIn('track_neutralization', rows[8]['exclusion_reasons'])

    def test_unclosed_red_flag_extends_to_end_conservatively(self):
        annotated, _, _ = self.run_filter([message(8, 30, 'RED FLAG', flag='RED', scope='Track', category='Flag')])
        rows = self.by_lap(annotated)
        for lap in (8, 9, 10):
            self.assertIn('track_neutralization', rows[lap]['exclusion_reasons'])
            self.assertIn('unclosed_neutralization', rows[lap]['quality_warnings'])
        self.assertTrue(rows[7]['calibration_eligible'])

    def test_local_yellow_only_warns_and_unpaired_clear_is_reported(self):
        rc = [message(3, 40, 'YELLOW IN TRACK SECTOR 4', flag='YELLOW', scope='Sector', sector=4, category='Flag'),
              message(3, 80, 'CLEAR IN TRACK SECTOR 4', flag='CLEAR', scope='Sector', sector=4, category='Flag'),
              message(8, 50, 'CLEAR IN TRACK SECTOR 9', flag='CLEAR', scope='Sector', sector=9, category='Flag')]
        annotated, _, report = self.run_filter(rc)
        rows = self.by_lap(annotated)
        self.assertTrue(rows[3]['calibration_eligible'])
        self.assertIn('local_yellow_overlap', rows[3]['quality_warnings'])
        self.assertTrue(rows[8]['calibration_eligible'])
        self.assertIn('unpaired_clear_in_lap', rows[8]['quality_warnings'])
        self.assertEqual(len(report['race_control_anomalies']), 1)

    def test_rainfall_during_lap_excludes_it(self):
        weather = [{'date': at(4, 30), 'rainfall': 1}, {'date': at(2, 30), 'rainfall': 0}]
        annotated, _, _ = self.run_filter(weather=weather)
        rows = self.by_lap(annotated)
        self.assertIn('rainfall', rows[4]['exclusion_reasons'])
        self.assertTrue(rows[2]['calibration_eligible'])


if __name__ == '__main__':
    unittest.main()
