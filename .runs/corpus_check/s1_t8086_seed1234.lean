import Mathesis.Basic

theorem s1_t8086 : (MOr MTrue MTrue) := (MAnd.intro MTrue.intro (MAnd.intro (MOr.inr MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)))