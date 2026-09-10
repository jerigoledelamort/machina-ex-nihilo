import Mathesis.Basic

theorem s2_t9730 : (MAnd MTrue (MAnd MTrue (MOr MTrue MTrue))) := (MAnd.intro MTrue.intro (MAnd.intro MTrue.intro (MOr.inr MTrue.intro)))