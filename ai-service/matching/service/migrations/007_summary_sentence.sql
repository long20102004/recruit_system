-- prep-1.1 (T15): cau cua `summary` - ung vien phia CV cua B5 (thiet ke 07 muc 5.4).
-- Giu text_raw (giu dau, hoa/thuong) lam dau vao BERTScore va bang chung Explain. Xoa CV -> xoa het.
CREATE TABLE cv_summary_sentence (
    cv_id         uuid NOT NULL REFERENCES cv ON DELETE CASCADE,
    idx           int NOT NULL,
    text          text NOT NULL,
    text_raw      text NOT NULL,
    has_negation  boolean NOT NULL DEFAULT false,
    is_coursework boolean NOT NULL DEFAULT false,
    PRIMARY KEY (cv_id, idx)
);
