import Mathesis.Basic

theorem s2_t8928 : (MAnd (MOr (MOr MTrue MTrue) MTrue) (MOr MTrue MTrue)) := (MAnd.intro (MOr.inr MTrue.intro) (MOr.inl MTrue.intro))