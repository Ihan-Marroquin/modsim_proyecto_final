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
    validation = sub.add_parser('validate', help='Validar el modelo congelado en el stint 3 reservado (LP-03; requiere download, reconcile, partition)')
    validation.add_argument('--output-dir', default='results/validation')
    experiments = sub.add_parser('experiments', help='Ejecutar A/B/C/D con 30 semillas reservadas por condición (LP-04/LP-05)')
    experiments.add_argument('--output-dir', default='results/experiments')
    compare = sub.add_parser('compare', help='Demo: estrategia histórica contra la candidata congelada (LG-02)')
    compare.add_argument('--degradation-multiplier', type=float, default=1.0)
    compare.add_argument('--candidate', default='docs/evidence/optimization/candidate.json')
    figures = sub.add_parser('figures', help='Generar las figuras del informe desde la evidencia (LG-01)')
    figures.add_argument('--output-dir', default='report/figures')
    args = parser.parse_args()
    if args.command == 'compare':
        from src.model import simulate_bahrain_case
        candidate = strategy_from_dict(json.loads((ROOT / args.candidate).read_text(encoding='utf-8')))
        runs = {role: simulate_bahrain_case(root_dir=ROOT, degradation_multiplier=args.degradation_multiplier,
                                            strategy=strategy)
                for role, strategy in (('historica', None), ('candidata', candidate))}
        base = runs['historica']['summary']['total_simulated_time_s']
        cand = runs['candidata']['summary']['total_simulated_time_s']
        mejora = base - cand
        print(json.dumps({
            'modo': 'determinista, tendencia trend_fuel_reference',
            'degradation_multiplier': args.degradation_multiplier,
            'observado_FIA_s': runs['historica']['summary']['official_reference_time_s'],
            'historica_simulada': {'paradas': runs['historica']['strategy']['stops_after_lap'],
                                   'total_s': base},
            'candidata_simulada': {'paradas': runs['candidata']['strategy']['stops_after_lap'],
                                   'total_s': cand},
            'mejora_s': round(mejora, 4),
            'mejora_pct': round(100 * mejora / base, 5),
        }, indent=2, ensure_ascii=False))
        print('mejora_s = base - candidata (positivo: candidata más rápida). La candidata es una predicción del '
              'modelo, nunca se observó; ver docs/validacion_experimentos.md para su incertidumbre.')
        return
    if args.command == 'figures':
        from src.visualization import make_figures
        produced = make_figures(ROOT, ROOT / args.output_dir)
        print(json.dumps(produced, indent=2, ensure_ascii=False))
        if produced['fig1_validacion'] is None:
            print('Figura 1 omitida: ejecutar antes download, reconcile, partition y validate.')
        return
    if args.command == 'validate':
        from src.validation import run_validation
        out = ROOT / args.output_dir
        report = run_validation(ROOT, out)
        main_scenario = report['by_scenario'][report['main_scenario']]
        keys = ('n_laps', 'MAE_s', 'bias_s', 'cumulative_error_s')
        print(json.dumps({
            'main_scenario': report['main_scenario'],
            'reserved_validation': {name: {k: round(v[k], 4) for k in keys}
                                    for name, v in main_scenario['reserved_validation'].items()},
            'full_race_reconstruction_not_validation': {
                k: round(main_scenario['full_race_reconstruction'][k], 4)
                for k in ('simulated_total_s', 'official_total_fia_s', 'simulated_minus_official_s')},
            'second_pit_check': {k: round(main_scenario['second_pit_check'][k], 4)
                                 for k in ('implied_additional_pit_loss_s', 'calibrated_additional_pit_loss_s')},
            'trend_sensitivity': [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()
                                   if k in ('trend_scenario', 'validation_all_MAE_s', 'validation_all_bias_s',
                                            'validation_all_cumulative_error_s')}
                                  for row in report['trend_sensitivity']],
        }, indent=2, ensure_ascii=False))
        print(f'Detalle: {out.relative_to(ROOT)} (validacion.json; la tabla por vuelta tiene tiempos de las fuentes y no se versiona)')
        return
    if args.command == 'experiments':
        from src.experiments import run_experiments
        out = ROOT / args.output_dir
        report = run_experiments(ROOT, out)
        main_results = report['results_by_trend_scenario'][report['design']['main_trend_scenario']]
        print(json.dumps({
            'seeds': [report['design']['evaluation_seeds'][0], report['design']['evaluation_seeds'][-1]],
            'replicates_per_condition': report['design']['replicates_per_condition'],
            'mean_total_time_s': {c: round(v['total_time_s']['mean'], 4)
                                  for c, v in main_results['by_condition'].items()},
            'sd_total_time_s': {c: round(v['total_time_s']['sd'], 4)
                                for c, v in main_results['by_condition'].items()},
            'paired_mejora_s': {p: {'mean': round(v['mejora_s']['mean'], 4), 'sd': v['mejora_s']['sd'],
                                    'mejora_pct': round(v['mejora_pct']['mean'], 5)}
                                for p, v in main_results['by_pair'].items()},
            'parameter_uncertainty_se_s': {m: round(v['se_s'], 4) for m, v in report['parameter_uncertainty'].items()
                                           if isinstance(v, dict)},
            'trend_sensitivity_mejora_s': {s: {p: round(v['deterministic_mejora_s'], 4) for p, v in r['by_pair'].items()}
                                           for s, r in report['results_by_trend_scenario'].items()},
        }, indent=2, ensure_ascii=False))
        print(f'Réplicas, pares, sensibilidad y resumen: {out.relative_to(ROOT)}')
        print('La dispersión pareada es casi cero porque el ruido compartido se cancela; no mide incertidumbre de parámetros.')
        return
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
