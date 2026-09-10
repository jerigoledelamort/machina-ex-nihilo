import Mathesis.Basic

theorem s2_t10800 : (MOr (MOr (MOr MTrue MTrue) (MOr MTrue MTrue)) (MAnd MTrue (MAnd MTrue MTrue))) := (MOr.inr (MAnd.intro MTrue.intro (MAnd.intro MTrue.intro MTrue.intro)))