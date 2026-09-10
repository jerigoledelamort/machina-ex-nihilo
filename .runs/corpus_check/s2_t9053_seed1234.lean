import Mathesis.Basic

theorem s2_t9053 : (MAnd (MOr (MOr MTrue MTrue) MTrue) MTrue) := (MAnd.intro (MOr.inl (MOr.inl MTrue.intro)) MTrue.intro)