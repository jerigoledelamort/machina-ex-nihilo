import Mathesis.Basic

theorem s1_t8200 : MTrue := (MAnd.intro (MOr.inr (MOr.inl MTrue.intro)) (MAnd.intro MTrue.intro (MOr.inr MTrue.intro)))