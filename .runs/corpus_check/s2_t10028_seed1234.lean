import Mathesis.Basic

theorem s2_t10028 : (MOr (MOr (MOr MTrue MTrue) (MOr MTrue MTrue)) (MAnd (MAnd MTrue MTrue) (MAnd MTrue MTrue))) := (MOr.inl (MOr.inl (MOr.inr MTrue.intro)))