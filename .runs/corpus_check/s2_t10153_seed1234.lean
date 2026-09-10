import Mathesis.Basic

theorem s2_t10153 : (MAnd (MOr MTrue (MOr MTrue MTrue)) (MOr MTrue (MOr MTrue MTrue))) := (MAnd.intro (MOr.inr (MOr.inr MTrue.intro)) (MOr.inr (MOr.inr MTrue.intro)))