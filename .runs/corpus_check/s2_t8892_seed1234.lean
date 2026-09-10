import Mathesis.Basic

theorem s2_t8892 : (MOr (MAnd (MAnd MTrue MTrue) MTrue) (MOr (MAnd MTrue MTrue) (MAnd MTrue MTrue))) := (MOr.inr (MOr.inr (MAnd.intro MTrue.intro MTrue.intro)))