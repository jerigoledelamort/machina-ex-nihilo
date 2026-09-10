# DECISIONS — Decision Log (spec section 61)

Формат: ID | Date | Question | Options | Evidence | Decision | Reason | Experiment

---

## D-001 | 2026-09-10 | Какую версию Lean зафиксировать для Milestone 1?

- **Options:** latest stable / конкретный LTS / Mathlib-совместимая версия
- **Evidence:** `elan` stable на 2026-09-10 = Lean 4.33.1 (commit 819816b2)
- **Decision:** Lean 4.33.1, зафиксирована в `lean/mathesis-lean/lean-toolchain` и `configs/default.yaml`
- **Reason:** минимальный environment без Mathlib (§11, §60) → нет нужды подгоняться под Mathlib; stable — минимальный риск
- **Experiment:** version fingerprint входит в `environment_hash`

## D-002 | 2026-09-10 | Где размещать Lean toolchain?

- **Options:** системная установка elan (~/.elan) / workspace-local ELAN_HOME
- **Evidence:** правило изоляции окружения; 64 GB RAM, диск D:
- **Decision:** workspace-local `.tools/elan` (ELAN_HOME указывается во всех процессах)
- **Reason:** ничего не устанавливается вне рабочей директории; environment полностью переносим и воспроизводим

## D-003 | 2026-09-10 | Механизм batch verification?

- **Options:** `lean` напрямую с ручным LEAN_PATH / `lake env lean` в фиксированном пакете
- **Evidence:** smoke-тесты 11/11; fresh process на каждый вызов
- **Decision:** `lake env lean <file>` из `lean/mathesis-lean`, fresh process, timeout из config
- **Reason:** lake корректно выставляет LEAN_PATH для собранных oleans; fresh process удовлетворяет §15/§18
- **Experiment:** полный batch/interactive benchmark — Stage 1 (§16)

## D-004 | 2026-09-10 | Классификация некатегоризованных ошибок Lean?

- **Options:** отдельный статус / fallback на FAIL_TYPECHECK
- **Evidence:** Lean не даёт машиночитаемого кода ошибки в текстовом выводе
- **Decision:** fallback → FAIL_TYPECHECK, raw message всегда сохраняется в diagnostics
- **Reason:** §12 фиксирует закрытый список статусов; raw message сохраняется для последующего уточнения классификации (§29)

## D-005 | 2026-09-10 | Interactive backend: Pantograph vs собственный REPL-процесс на Lean API?

- **Options:** (a) Pantograph как Lean-зависимость; (b) собственный REPL-исполняемый файл на базе `Lean.Elab`/`Lean.Meta`
- **Evidence:** собственный REPL реализован и протестирован (20/20); Lean benchmark 2026-09-10:
  warm interactive verify 0.5–62 ms против batch 620–790 ms (ускорение 10–1200x в зависимости от размера);
  search throughput ~860 actions/sec на реалистичных последовательностях. Pantograph не требовался:
  `Lean.Elab.process` + `importModules(loadExts := true)` полностью покрывают потребности Milestone 1.
- **Decision:** собственный REPL (`Mathesis.ReplMain`, persistent process, JSON-lines over stdio).
  Импорты загружаются один раз при старте (argv); reset = перезапуск процесса Python-обёрткой.
- **Reason:** нулевая внешняя зависимость (§60); полный контроль над протоколом; измеренная производительность
  с большим запасом для rollout budget. Ограничение: command-level гранулярность; tactic-level actions
  (§33) будут добавлены в Stage 4 поверх той же сессии.
- **Experiment:** benchmarks/results/lean_benchmark_20260910_*.json

## D-006 | 2026-09-10 | Ограничение архитектуры REPL: один importModules на процесс

- **Options:** (a) повторный `importModules (loadExts := true)` в живом процессе; (b) импорты один раз при старте, reset через перезапуск
- **Evidence:** повторный вызов в живом процессе приводит к зависанию/некорректной ре-инициализации
  (документация Lean: небезопасно выполнять initializer code повторно; `withImporting` сбрасывает флаг).
- **Decision:** (b). Imports фиксируются при создании сессии; `load_environment()` со сменой импортов = новый session; `reset()` = kill + respawn.
- **Reason:** соответствие §11 (environment фиксирован на experiment) и §64 (crash/respawn — infrastructure event).
- **Experiment:** tests/test_interactive_backend.py (reset, crash recovery)
