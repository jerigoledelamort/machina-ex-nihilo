import Mathesis.Basic

theorem s2_m11322 : (MOr (MAnd (MAnd MTrue MTrue) MTrue) (MOr (MAnd MTrue MTrue) MTrue)) := (MOr.inr (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) MTrue.intro))