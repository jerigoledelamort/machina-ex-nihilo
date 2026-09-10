import Mathesis.Basic

theorem s2_m11300 : (MAnd (MOr (MOr MTrue MTrue) (MAnd MTrue MTrue)) (MOr (MOr MTrue MTrue) (MOr MTrue MTrue))) := (MOr.inr (MOr.inr (MOr.inr MTrue.intro)))