import Mathesis.Basic

theorem s2_t10722 : (MOr (MAnd MTrue (MAnd MTrue MTrue)) (MAnd MTrue MTrue)) := (MOr.inr (MAnd.intro MTrue.intro MTrue.intro))