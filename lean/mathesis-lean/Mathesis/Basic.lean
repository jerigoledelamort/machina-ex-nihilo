/-
Минимальный environment Mathesis Milestone 1.

Содержит только структурные определения, необходимые corpus generator'у
(§21): разрешены binders, Π-types, equality, inductive types, universes.
Запрещено кодировать математические теории (Nat arithmetic, groups и т.д.).
-/

-- Базовый структурный индуктивный тип для генерации AST-уровня S0/S1
inductive MUnit : Type where
  | mk : MUnit

-- Простейшая пропозициональная структура (Prop, §7)
inductive MFalse : Prop where

inductive MTrue : Prop where
  | intro : MTrue

inductive MAnd (a b : Prop) : Prop where
  | intro : a → b → MAnd a b

inductive MOr (a b : Prop) : Prop where
  | inl : a → MOr a b
  | inr : b → MOr a b

-- Equality как встроенный механизм ядра используется напрямую (Eq, §7)
