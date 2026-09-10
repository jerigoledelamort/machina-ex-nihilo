import Mathesis.Basic

theorem s2_t10863 : (MAnd (MAnd (MAnd MTrue MTrue) MTrue) (MOr (MOr MTrue MTrue) (MOr MTrue MTrue))) := (MAnd.intro (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) MTrue.intro) (MOr.inl (MOr.inl MTrue.intro)))