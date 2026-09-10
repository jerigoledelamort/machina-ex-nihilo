import Mathesis.Basic

theorem s2_m11267 : (MAnd (MAnd (MOr MTrue MTrue) (MOr MTrue MTrue)) MTrue) := (MOr.inl (MAnd.intro (MOr.inr MTrue.intro) (MOr.inl MTrue.intro)))