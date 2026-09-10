import Mathesis.Basic

theorem s2_t8830 : (MAnd (MAnd (MOr MTrue MTrue) MTrue) MTrue) := (MAnd.intro (MAnd.intro (MOr.inl MTrue.intro) MTrue.intro) MTrue.intro)