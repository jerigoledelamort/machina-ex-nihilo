import Mathesis.Basic

theorem s1_t8263 : (MAnd (MAnd MTrue (MOr MTrue MTrue)) (MOr (MOr MTrue MTrue) MTrue)) := (MOr.inr (MOr.inl MTrue.intro))