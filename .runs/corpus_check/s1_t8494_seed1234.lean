import Mathesis.Basic

theorem s1_t8494 : (MAnd (MAnd MTrue (MOr MTrue MTrue)) MTrue) := (MOr.inr (MAnd.intro MTrue.intro MTrue.intro))