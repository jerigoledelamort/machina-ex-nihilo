import Mathesis.Basic

theorem s1_t8234 : (MAnd (MOr MTrue MTrue) (MAnd MTrue MTrue)) := (MOr.inr (MOr.inl MTrue.intro))