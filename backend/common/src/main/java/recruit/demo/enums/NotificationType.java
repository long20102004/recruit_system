package recruit.demo.enums;

/** Loại thông báo người dùng bật/tắt ở màn C14; mặc định khi chưa cấu hình. */
public enum NotificationType {
    APPLICATION_STATUS(true, true, "application"),
    INTERVIEW_INVITE(true, true, "interview"),
    JOB_ALERT(true, true, "alert"),
    COMPANY_INVITE(true, true, "company"),
    COMPANY_STATUS(true, true, "company"),
    JOB_MODERATION(true, true, "company"),
    CV_PROCESSED(true, false, "cv");

    private final boolean defaultInApp;
    private final boolean defaultEmail;
    private final String category;

    NotificationType(boolean defaultInApp, boolean defaultEmail, String category) {
        this.defaultInApp = defaultInApp;
        this.defaultEmail = defaultEmail;
        this.category = category;
    }

    public boolean defaultInApp() { return defaultInApp; }

    public boolean defaultEmail() { return defaultEmail; }

    public String category() { return category; }
}
