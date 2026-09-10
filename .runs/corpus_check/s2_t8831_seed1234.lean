import Mathesis.Basic

theorem s2_t8831 : (MAnd (MOr MTrue MTrue) (MOr MTrue MTrue)) := (MAnd.intro (MOr.inl MTrue.intro) (MOr.inl MTrue.intro))