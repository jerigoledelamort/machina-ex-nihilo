import Mathesis.Basic

theorem s2_t9541 : (MOr (MOr (MAnd MTrue MTrue) (MAnd MTrue MTrue)) (MAnd (MAnd MTrue MTrue) (MAnd MTrue MTrue))) := (MOr.inr (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)))