import Mathesis.Basic

theorem s2_m81 : (MOr (MAnd MTrue MTrue) (MOr MTrue MTrue)) := (MOr.inl (MOr.inr MTrue.intro))