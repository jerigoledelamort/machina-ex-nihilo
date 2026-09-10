import Mathesis.Basic

theorem s2_t9852 : (MAnd (MOr (MOr MTrue MTrue) (MAnd MTrue MTrue)) (MOr MTrue MTrue)) := (MAnd.intro (MOr.inr (MAnd.intro MTrue.intro MTrue.intro)) (MOr.inr MTrue.intro))