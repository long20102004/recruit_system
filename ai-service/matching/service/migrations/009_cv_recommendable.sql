-- S07 / V-21: ung vien dong y nhan goi y viec lam (tin moi -> Luong C tren kho CV co co nay).
-- Co theo NGUOI: moi ban cua cung candidate_key mang cung gia tri (PATCH /cv/{id} doi ca nhom; ban moi ke thua).
ALTER TABLE cv ADD COLUMN recommendable boolean NOT NULL DEFAULT false;
CREATE INDEX cv_recommendable_idx ON cv (recommendable) WHERE recommendable;
