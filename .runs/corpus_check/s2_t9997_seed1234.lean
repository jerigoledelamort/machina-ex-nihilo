import Mathesis.Basic

theorem s2_t9997 : (MOr (MOr MTrue (MOr MTrue MTrue)) (MOr (MOr MTrue MTrue) (MOr MTrue MTrue))) := (MOr.inr (MOr.inl (MOr.inr MTrue.intro)))