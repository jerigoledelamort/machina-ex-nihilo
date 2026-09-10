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

## D-007 | 2026-09-10 | Tokenizer: BPE vs Lean-aware?

- **Options:** (a) BPE (HF tokenizers, ByteLevel, vocab 8000, обучен на corpus_tokenizer.jsonl); (b) Lean-aware (словарный: теги proof-state, ключевые слова, операторы, атомарные идентификаторы, char-fallback)
- **Evidence:** tokenizer A/B benchmark на 1006 декларациях + 575 ошибках (benchmarks/results/tokenizer_benchmark_*.json):
  * compression ratio: BPE 3.173 vs Lean-aware 2.805 (Lean-aware ХУЖЕ на 11.6%)
  * tokens/proof: Lean-aware лучше (13.9 vs 18.4); tokens/declaration: BPE лучше (41.0 vs 46.4)
  * inference throughput: Lean-aware быстрее (5.3M vs 3.3M chars/s), vocab 89 vs 8000
- **Decision:** **BPE** — default tokenizer Milestone 1
- **Reason:** pre-registered критерий §30: Lean-aware выбирается только при ≥20% улучшении compression ratio;
  фактически −11.6% → критерий не выполнен. Преимущество Lean-aware на proofs (−25% tokens) недостаточно
  против общего проигрыша по compression; переоткрытие вопроса возможно через ablation на Stage 6/7
  (OBSERVATION → EXPERIMENT → DECISION).
- **Experiment:** scripts/tokenizer_benchmark.py, data/corpus_tokenizer.jsonl

## D-008 | 2026-09-10 | Error normalization: структура и fallback?

- **Options:** (a) только raw text; (b) нормализованное представление с raw fallback
- **Evidence:** типовые ошибки Lean (type mismatch, unknown identifier, parse error) reliably
  структурируются regex-паттернами; hint-тексты извлекаются; неструктурируемые сохраняются как raw_message
- **Decision:** (b) — NormalizedError{error_type, location, expected_type, actual_type, message, hint, raw_message};
  raw_message сохраняется всегда (§29); версия Lean — часть experiment metadata
- **Reason:** §29 прямо требует нормализацию с fallback
- **Experiment:** tests/test_errors_tokenizers.py

## D-006 | 2026-09-10 | Ограничение архитектуры REPL: один importModules на процесс

- **Options:** (a) повторный `importModules (loadExts := true)` в живом процессе; (b) импорты один раз при старте, reset через перезапуск
- **Evidence:** повторный вызов в живом процессе приводит к зависанию/некорректной ре-инициализации
  (документация Lean: небезопасно выполнять initializer code повторно; `withImporting` сбрасывает флаг).
- **Decision:** (b). Imports фиксируются при создании сессии; `load_environment()` со сменой импортов = новый session; `reset()` = kill + respawn.
- **Reason:** соответствие §11 (environment фиксирован на experiment) и §64 (crash/respawn — infrastructure event).
- **Experiment:** tests/test_interactive_backend.py (reset, crash recovery)
