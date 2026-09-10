import Mathesis.Basic

theorem s2_m11332 : (MOr (MOr MTrue (MAnd MTrue MTrue)) (MOr (MOr MTrue MTrue) MTrue)) := (MOr.inr (MOr.inr (MAnd.intro MTrue.intro MTrue.intro)))