import Mathesis.Basic

theorem s2_t9663 : (MAnd (MOr (MOr MTrue MTrue) (MOr MTrue MTrue)) (MOr (MAnd MTrue MTrue) (MOr MTrue MTrue))) := (MAnd.intro (MOr.inl (MOr.inr MTrue.intro)) (MOr.inr (MOr.inl MTrue.intro)))