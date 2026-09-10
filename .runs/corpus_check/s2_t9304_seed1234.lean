import Mathesis.Basic

theorem s2_t9304 : (MAnd (MOr MTrue (MOr MTrue MTrue)) (MAnd (MOr MTrue MTrue) (MAnd MTrue MTrue))) := (MAnd.intro (MOr.inr (MOr.inl MTrue.intro)) (MAnd.intro (MOr.inr MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)))