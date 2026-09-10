import Mathesis.Basic

theorem s1_t8036 : (MOr (MAnd (MOr MTrue MTrue) (MAnd MTrue MTrue)) (MOr MTrue (MOr MTrue MFalse))) := (MOr.inr (MAnd.intro MTrue.intro (MAnd.intro MTrue.intro MTrue.intro)))