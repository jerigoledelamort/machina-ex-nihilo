import Mathesis.Basic

theorem s2_t9415 : (MOr (MOr (MAnd MTrue MTrue) (MAnd MTrue MTrue)) (MOr (MOr MTrue MTrue) (MOr MTrue MTrue))) := (MOr.inl (MOr.inl (MAnd.intro MTrue.intro MTrue.intro)))