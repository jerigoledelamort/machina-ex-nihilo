import Mathesis.Basic

theorem s1_t8654 : (MOr (MOr (MOr MTrue MTrue) MTrue) (MOr MTrue (MAnd MTrue MTrue))) := (MAnd.intro (MOr.inl (MOr.inl MTrue.intro)) MTrue.intro)