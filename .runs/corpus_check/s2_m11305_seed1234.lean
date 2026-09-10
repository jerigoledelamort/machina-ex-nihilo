import Mathesis.Basic

theorem s2_m11305 : (MOr (MAnd (MOr MTrue MFalse) (MOr MTrue MFalse)) (MOr MTrue MTrue)) := (MOr.inl (MAnd.intro (MOr.inr MTrue.intro) (MOr.inl MTrue.intro)))