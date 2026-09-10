import Mathesis.Basic

theorem s2_t9299 : (MOr MTrue (MAnd (MOr MTrue MTrue) (MAnd MTrue MTrue))) := (MOr.inr (MAnd.intro (MOr.inl MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)))