import Mathesis.Basic

theorem s2_t9114 : (MOr MTrue (MAnd (MOr MTrue MTrue) (MOr MTrue MTrue))) := (MOr.inr (MAnd.intro (MOr.inl MTrue.intro) (MOr.inl MTrue.intro)))