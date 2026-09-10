import Mathesis.Basic

theorem s2_t8984 : (MAnd (MOr (MOr MTrue MTrue) MTrue) MTrue) := (MAnd.intro (MOr.inr MTrue.intro) MTrue.intro)