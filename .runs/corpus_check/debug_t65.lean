import Mathesis.Basic

theorem s2_t65 : (MAnd (MAnd MTrue MTrue) MTrue) := (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) MTrue.intro)
