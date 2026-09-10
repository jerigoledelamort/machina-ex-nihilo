import Mathesis.Basic

theorem s2_t9911 : (MOr (MAnd (MAnd MTrue MTrue) MTrue) (MAnd (MOr MTrue MTrue) MTrue)) := (MOr.inl (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) MTrue.intro))