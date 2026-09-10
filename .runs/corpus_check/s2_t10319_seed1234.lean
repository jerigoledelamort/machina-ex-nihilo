import Mathesis.Basic

theorem s2_t10319 : (MAnd (MAnd (MAnd MTrue MTrue) (MAnd MTrue MTrue)) (MOr (MOr MTrue MTrue) (MAnd MTrue MTrue))) := (MAnd.intro (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)) (MOr.inl (MOr.inl MTrue.intro)))