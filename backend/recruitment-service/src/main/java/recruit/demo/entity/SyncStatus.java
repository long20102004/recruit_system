package recruit.demo.entity;

/** Trang thai dong bo mot CV / JD sang cvmatch (plan I05). */
public enum SyncStatus {
    /** Can gui (moi doi, hoac backfill). */
    PENDING,
    /** cvmatch da co ban moi nhat. */
    SYNCED,
    /** cvmatch tra 422 (sai schema / thieu noi dung): khong thu lai den khi du lieu doi. */
    INVALID,
    /** Loi tam thoi (mang, 5xx): scheduler thu lai. */
    FAILED,
    /** Da xoa ben cvmatch. */
    DELETED
}
