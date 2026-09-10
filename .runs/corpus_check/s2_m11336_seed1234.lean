import Mathesis.Basic

theorem s2_m11336 : (MOr (MAnd (MOr MTrue MTrue) MTrue) (MOr MTrue MTrue)) := (MAnd.intro (MAnd.intro (MOr.inl MTrue.intro) MTrue.intro) (MOr.inl MTrue.intro))