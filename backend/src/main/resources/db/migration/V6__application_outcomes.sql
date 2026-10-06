-- Terminal-stage outcomes on the tracker. The pipeline has always known *where* a
-- card sits (offer / rejected) but never *why* or *for how much*; these two columns
-- let the loop close -- a rejection reason feeds back into what to improve, and an
-- offer's compensation is the number to compare and negotiate against.
ALTER TABLE applications ADD COLUMN offer_compensation text;
ALTER TABLE applications ADD COLUMN rejection_reason text;
