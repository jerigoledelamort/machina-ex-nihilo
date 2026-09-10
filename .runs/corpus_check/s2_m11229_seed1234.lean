import Mathesis.Basic

theorem s2_m11229 : (MAnd (MOr (MOr MTrue MTrue) (MOr MTrue MTrue)) (MAnd (MAnd MTrue MTrue) (MOr MTrue MTrue))) := (MOr.inl (MOr.inl (MOr.inr MTrue.intro)))