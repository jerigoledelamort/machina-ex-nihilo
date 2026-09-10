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

## D-005 | OPEN | Interactive backend: Pantograph vs собственный REPL-процесс на Lean API?

- **Options:** (a) Pantograph как Lean-зависимость; (b) собственный REPL-исполняемый файл на базе `Lean.Elab`/`Lean.Meta`
- **Evidence:** не собрано
- **Decision:** отложено до Lean benchmark (§16–§17); batch-линия не зависит от этого решения
- **Reason:** §3/§61: решение влияет на эксперимент → сначала benchmark, затем выбор; зафиксировать uncertainty
- **Experiment:** Lean Interactive Benchmark (Stage 1, §16–§17)
