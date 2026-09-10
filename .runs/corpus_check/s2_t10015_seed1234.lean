import Mathesis.Basic

theorem s2_t10015 : (MOr (MAnd MTrue (MOr MTrue MTrue)) (MAnd MTrue MTrue)) := (MOr.inl (MAnd.intro MTrue.intro (MOr.inl MTrue.intro)))