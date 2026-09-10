import Mathesis.Basic

theorem s2_t9923 : (MOr (MOr MTrue (MOr MTrue MTrue)) (MAnd (MOr MTrue MTrue) (MOr MTrue MTrue))) := (MOr.inr (MAnd.intro (MOr.inr MTrue.intro) (MOr.inr MTrue.intro)))