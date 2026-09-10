import Mathesis.Basic

theorem s2_t10305 : (MOr (MOr (MOr MTrue MTrue) (MOr MTrue MTrue)) (MAnd (MOr MTrue MTrue) MTrue)) := (MOr.inr (MAnd.intro (MOr.inl MTrue.intro) MTrue.intro))