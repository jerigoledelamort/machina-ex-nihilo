import Mathesis.Basic

theorem s1_t8414 : (MAnd MTrue (MAnd MTrue (MAnd MTrue MTrue))) := (MOr.inl (MAnd.intro (MOr.inr MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)))