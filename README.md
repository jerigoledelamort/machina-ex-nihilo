# Mathesis Research System — Milestone 1

Экспериментальная система для исследования автономного накопления формального
математического знания. Milestone 1 исследует только **Prover**.

Master Technical Specification v4.0 — см. задачу проекта; ключевые документы:

- `FOUNDATION.md` — trusted computational substrate (Lean 4.33.1)
- `DECISIONS.md` — decision log
- `configs/default.yaml` — единственный источник experiment-параметров (§62)
- `.agent/current/execution_graph.md` — план выполнения

## Структура

```
lean/mathesis-lean/     минимальный Lean environment (без Mathlib, §11)
src/mathesis/
  config.py             versioned configuration (§62)
  lean_env.py           environment fingerprinting (§11)
  provenance.py         generator/validation provenance (§23)
  validation/           ProofValidator pipeline (§12), batch backend (§15),
                        safety / trusted-base inspection (§9)
tests/                  smoke-тесты validator
.tools/elan/            workspace-local Lean toolchain (не в git)
```

## Быстрый старт

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest tests/ -v
```

Lean toolchain уже установлен в `.tools/elan` (Lean 4.33.1). Для ручной сборки
Lean-пакета: `$env:ELAN_HOME="<workspace>\.tools\elan"; lake build`
в `lean/mathesis-lean`.

## Статус

Stage 1 (Lean Foundation) в процессе: batch-линия готова и протестирована;
interactive backend и Lean benchmark — следующие шаги.
