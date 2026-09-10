import Mathesis.Basic

theorem s2_t9244 : (MOr (MAnd (MOr MTrue MTrue) (MOr MTrue MTrue)) (MAnd (MAnd MTrue MTrue) (MOr MTrue MTrue))) := (MOr.inr (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) (MOr.inr MTrue.intro)))