import Mathesis.Basic

theorem s2_m11233 : (MOr MTrue (MOr (MOr MTrue MTrue) (MAnd MTrue MTrue))) := (MAnd.intro MTrue.intro (MOr.inl (MOr.inr MTrue.intro)))