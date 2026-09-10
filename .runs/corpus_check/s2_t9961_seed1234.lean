import Mathesis.Basic

theorem s2_t9961 : (MAnd (MAnd (MOr MTrue MTrue) (MAnd MTrue MTrue)) (MOr MTrue MTrue)) := (MAnd.intro (MAnd.intro (MOr.inr MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)) (MOr.inr MTrue.intro))