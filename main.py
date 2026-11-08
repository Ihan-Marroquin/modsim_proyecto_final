"""CLI inicial. Ejecutar desde la raíz del proyecto."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
from src.domain import Constraints, parameters_from_dict, strategy_from_dict
from src.simulation import simulate

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description='Proyecto F1: base inicial reproducible')
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='Ejemplo SINTÉTICO, sin validación real')
    demo.add_argument('--seed', type=int, default=42)
    demo.add_argument('--stochastic', action='store_true')
    download = sub.add_parser('download', help='Descargar el caso real candidato')
    download.add_argument('--provider', choices=['openf1', 'fastf1'], default='openf1')
    sub.add_parser('reconcile', help='Conciliar tiempos OpenF1 contra Jolpica/FIA (requiere download)')
    sub.add_parser('partition', help='Congelar partición entrenamiento/validación (requiere download)')
    sub.add_parser('inventory', help='Reconstruir inventario de neumáticos y contar estrategias factibles')
    sub.add_parser('calibrate', help='Calibrar parámetros reales solo con entrenamiento (requiere download, reconcile, partition)')
    sim = sub.add_parser('simulate', help='Simular carrera completa con parámetros reales calibrados (JO-03)')
    sim.add_argument('--scenario', choices=['trend_fuel_reference', 'trend_zero', 'trend_double'],
                     default='trend_fuel_reference', help='Escenario de tendencia calibrado')
    sim.add_argument('--stochastic', action='store_true', help='Activar modo estocástico con ruido gaussiano')
    sim.add_argument('--seed', type=int, default=42, help='Semilla para modo estocástico')
    sim.add_argument('--degradation-multiplier', type=float, default=1.0,
                     help='Multiplicador de degradación para análisis de sensibilidad')
    sim.add_argument('--strategy', type=str, default=None,
                     help='Ruta a archivo JSON de estrategia (por defecto usa la histórica)')
    sim.add_argument('--output-dir', type=str, default='results/simulation',
                     help='Directorio de salida para los resultados')
    search = sub.add_parser('optimize-demo', help='Probar el optimizador en un caso SINTÉTICO')
    search.add_argument('--seed', type=int, default=42)
    search.add_argument('--runs', type=int, default=1)
    calibrated_search = sub.add_parser('optimize', help='Ejecutar pilotos y recocido calibrado de Bahréin')
    calibrated_search.add_argument('--output-dir', default='results/optimization')
    args = parser.parse_args()
    if args.command == 'optimize':
        from src.optimization_case import run_calibrated_search
        out = ROOT / args.output_dir
        report = run_calibrated_search(ROOT, out)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f'Evidencia y candidata: {out}')
        return
    if args.command == 'download':
        config = json.loads((ROOT/'configs/case_bahrain_2024.json').read_text(encoding='utf-8'))
        if args.provider == 'openf1':
            from src.openf1_data import download_openf1_case
            report = download_openf1_case(config, ROOT)
        else:
            from src.data import download_case
            report = download_case(config, ROOT)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if args.command == 'reconcile':
        from src.reconciliation import reconcile_case
        config = json.loads((ROOT/'configs/case_bahrain_2024.json').read_text(encoding='utf-8'))
        report = reconcile_case(config, ROOT)
        print(json.dumps({k: report[k] for k in ('lap_comparison', 'reference_sum_equals_official_total',
                                                 'openf1_minus_official_s', 'pit_durations')},
                         indent=2, ensure_ascii=False))
        print('Detalle: results/data_audit/reconciliation.json y data/processed/lap_time_reconciliation.csv')
        return
    if args.command == 'partition':
        from src.partition import freeze_partition
        config = json.loads((ROOT/'configs/case_bahrain_2024.json').read_text(encoding='utf-8'))
        manifest = freeze_partition(config, ROOT)
        print(json.dumps({k: manifest[k] for k in ('training_laps', 'validation_laps', 'excluded_from_fit_laps',
                                                   'validation_covered_laps', 'validation_extrapolated_laps',
                                                   'coverage', 'identifiability_training', 'code_state')},
                         indent=2, ensure_ascii=False))
        print('Manifiesto: results/data_audit/partition_manifest.json; partición: data/processed/partition_split.csv')
        return
    if args.command == 'inventory':
        from src.inventory import inventory_report
        config = json.loads((ROOT/'configs/case_bahrain_2024.json').read_text(encoding='utf-8'))
        tyres = json.loads((ROOT/'configs/tyre_inventory_bahrain_2024.json').read_text(encoding='utf-8'))
        report = inventory_report(config, tyres, ROOT)
        print(json.dumps({k: report[k] for k in ('sets_used_before_race', 'new_sets_unused_before_race',
                                                 'race_stint_limits_observed', 'search_space')},
                         indent=2, ensure_ascii=False))
        print('Detalle: results/data_audit/tyre_inventory.json')
        return
    if args.command == 'calibrate':
        from src.calibration import calibrate_case
        config = json.loads((ROOT/'configs/case_bahrain_2024.json').read_text(encoding='utf-8'))
        output = calibrate_case(config, ROOT)
        print(json.dumps({'parameters': output['parameters'],
                          'sensitivity_parameters': output['sensitivity_parameters'],
                          'validation_laps_read': output['data_audit']['validation_laps_read']},
                         indent=2, ensure_ascii=False))
        print('Parámetros: configs/params_bahrain_2024.json; detalle: results/data_audit/calibration.json')
        return
    if args.command == 'simulate':
        from src.model import simulate_bahrain_case
        from src.data import write_csv
        strategy_obj = None
        if args.strategy:
            strat_data = json.loads(Path(args.strategy).read_text(encoding='utf-8'))
            strategy_obj = strategy_from_dict(strat_data)
        report = simulate_bahrain_case(
            root_dir=ROOT,
            scenario=args.scenario,
            stochastic=args.stochastic,
            seed=args.seed,
            degradation_multiplier=args.degradation_multiplier,
            strategy=strategy_obj,
        )
        out_dir = ROOT / args.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / 'bahrain_2024_simulation.json'
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        csv_path = out_dir / 'bahrain_2024_laps.csv'
        write_csv(csv_path, report['laps'])
        print(json.dumps({
            'case': report['case'],
            'driver': report['driver'],
            'scenario': report['scenario'],
            'stochastic': report['stochastic'],
            'seed': report['seed'],
            'degradation_multiplier': report['degradation_multiplier'],
            'strategy': report['strategy']['name'],
            'stops_after_lap': report['strategy']['stops_after_lap'],
            'summary': report['summary'],
            'output_json': str(json_path.relative_to(ROOT)),
            'output_csv': str(csv_path.relative_to(ROOT)),
        }, indent=2, ensure_ascii=False))
        return
    config = json.loads((ROOT/'configs/synthetic_demo.json').read_text(encoding='utf-8'))
    if args.command == 'optimize-demo':
        from src.optimization import enumerate_reference, optimize
        from src.data import write_csv
        if args.runs < 1:
            parser.error('--runs debe ser positivo')
        limits = Constraints(**config['constraints'])
        params = parameters_from_dict(config['parameters'])
        initial = strategy_from_dict(config['strategy'])
        reference = enumerate_reference(initial, params, limits)
        out = ROOT/'results/optimizer_demo'
        out.mkdir(parents=True, exist_ok=True)
        summaries = []
        for seed in range(args.seed, args.seed + args.runs):
            result = optimize(initial, params, limits, seed=seed)
            write_csv(out/f'convergence_seed_{seed}.csv', result['history'])
            summaries.append({'seed': seed, 'best_time_s': result['best_time_s'],
                              'reference_time_s': reference['best_time_s'],
                              'gap_s': result['best_time_s'] - reference['best_time_s'],
                              'stops_after_lap': list(result['strategy'].stops_after_lap),
                              'objective_evaluations': result['objective_evaluations'],
                              'provenance': params.provenance})
            (out/f'best_seed_{seed}.json').write_text(json.dumps(asdict(result['strategy']), indent=2), encoding='utf-8')
        write_csv(out/'search_runs.csv', summaries)
        print(json.dumps({'runs': len(summaries), 'seeds': [summaries[0]['seed'], summaries[-1]['seed']],
                          'best_time_s': min(r['best_time_s'] for r in summaries),
                          'reference_time_s': reference['best_time_s'],
                          'max_gap_s': max(r['gap_s'] for r in summaries),
                          'output': 'results/optimizer_demo/search_runs.csv'}, indent=2))
        print('Resultados SINTÉTICOS; no constituyen experimentos finales ni mejora real de F1.')
        return
    result = simulate(strategy_from_dict(config['strategy']),
                      parameters_from_dict(config['parameters']),
                      Constraints(**config['constraints']), seed=args.seed,
                      stochastic=args.stochastic)
    out = ROOT/'results/demo'
    out.mkdir(parents=True, exist_ok=True)
    (out/'synthetic_demo.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    summary = {k: v for k, v in result.items() if k not in ['laps', 'events']}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print('Datos y parámetros SINTÉTICOS. No representan una validación de Bahréin.')


if __name__ == '__main__':
    main()
