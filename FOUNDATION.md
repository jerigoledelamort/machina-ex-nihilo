# FOUNDATION — Trusted Computational Substrate

Статус: документ аудита trusted base. Версия Lean зафиксирована: **4.33.1**
(x86_64-w64-windows-gnu, commit `819816b2e0a3bf405af45ae5c7af2491d8f5bee6`).

Главный принцип: результаты системы считаются **kernel-verified относительно
зафиксированного trusted base Lean**, а не «проверены нами».

## 1. Минимальный substrate (механизмы ядра Lean 4.33.1)

Ниже перечислены механизмы, которые Lean предоставляет как вычислительный
substrate. Это НЕ «пустой логический лист» — система строится поверх них.

| Механизм | Роль в substrate |
|---|---|
| `Prop` | вселенная пропозиций; импредикативность `Prop` — часть теории типов ядра |
| `Sort u` / `Type u` | иерархия вселенных; `Prop = Sort 0`, `Type u = Sort (u+1)` |
| Dependent function types (`Π`/`→`) | универсальный механизм построения зависимых типов |
| Equality (`Eq`, `Eq.refl`) | встроенное индуктивное отношение равенства ядра |
| Inductive types | механизм объявления индуктивных/рекурсивных структур (`inductive`, `structure`) |
| Universes | контроль размера типов, аккумуляция universe constraints |
| Elaboration / type checking | фронтенд: синтез метапеременных, instance resolution, приведение типов |
| Kernel reduction | `whnf`/`isDefEq`-редукция в ядре; финальная проверка термов |
| Recursor / structural recursion | механизмы вычислений для индуктивных типов |

Дополнительные механизмы конкретной версии Lean будут дополняться в этот
документ по результатам аудита (обязанность §7).

## 2. Kernel-level trusted principles (§8–§9)

Следующие константы являются частью ядра Lean и его стандартной аксиоматики.
Они НЕ являются «аксиомами, написанными пользователем»:

| Константа | Статус | Смысл |
|---|---|---|
| `Classical.choice` | TRUSTED KERNEL | классический выбор; основа классической логики |
| `propext` | TRUSTED KERNEL | экстенсиональность пропозиций (`a ↔ b → a = b`) |
| `Quot.sound` | TRUSTED KERNEL | экстенсиональность фактор-типов |

Результаты считаются kernel-verified **относительно** этого набора.
Использование фиксируется в `validation_provenance.kernel_axioms`.

## 3. Extended trusted base (запреты и ограничения)

| Механизм | Статус | Обработка в Milestone 1 |
|---|---|---|
| `Classical.choice`, `propext`, `Quot.sound` | TRUSTED KERNEL | разрешены; использование протоколируется |
| `native_decide` | RESTRICTED / EXTENDED TRUST | **запрещён** в proof pipeline; не эквивалентен kernel reduction |
| `unsafe` | FORBIDDEN | блокируется safety-сканом |
| `sorry` / `admit` | FORBIDDEN | блокируется safety-сканом |
| user-defined `axiom` | FORBIDDEN в обычном proof pipeline | блокируется safety-сканом; `AXIOM_CANDIDATE` возможен только в отдельном исследовательском pipeline (§10) |
| `opaque`, `implemented_by`, `extern`, `set_option` | FORBIDDEN | блокируются safety-сканом |
| произвольные `import` | FORBIDDEN | разрешены только `Mathesis.*` (минимальный environment, §11) |

## 4. Реализация проверок

Проверки реализованы в `src/mathesis/validation/safety.py` и покрыты тестами
(`tests/test_batch_backend.py`):

- safety-скан до elaboration (комментарии/строки вырезаются, чтобы избежать ложных срабатываний);
- import validation против минимального environment;
- trusted-base inspection через `#print axioms` после успешной kernel-проверки:
  зависимости вне {`Classical.choice`, `propext`, `Quot.sound`} → `FAIL_SAFETY`;
  зависимости из trusted-набора → протоколируются в `kernel_axioms`.

## 5. Режимы проверки (§13)

- **Batch** (`BatchBackend.verify_file`): fresh process, fixed environment.
  Финальная проверка, reproduction, milestone artifacts.
- **Interactive**: persistent session для proof search / process reward.
  Interactive SUCCESS **никогда** не заменяет batch verification.

## 6. Environment fingerprint (§11)

Каждая проверка фиксирует: Lean version, toolchain hash, lakefile hash,
manifest hash, source hash, environment hash (`src/mathesis/lean_env.py`).
Расширение environment во время эксперимента запрещено и детектируется
изменением `environment_hash`.
