import Mathesis.Basic

theorem s2_m11192 : (MAnd MTrue (MAnd (MAnd MTrue MTrue) (MOr MTrue MTrue))) := (MAnd.intro (MAnd.intro (MAnd.intro MTrue.intro MTrue.intro) (MOr.inr MTrue.intro)) MTrue.intro)