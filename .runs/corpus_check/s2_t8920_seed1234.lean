import Mathesis.Basic

theorem s2_t8920 : (MOr (MAnd MTrue MTrue) (MAnd MTrue (MAnd MTrue MTrue))) := (MOr.inl (MAnd.intro MTrue.intro MTrue.intro))