package recruit.demo.enums;

/** Loại thông báo người dùng bật/tắt ở màn C14; mặc định khi chưa cấu hình. */
public enum NotificationType {
    APPLICATION_STATUS(true, true),
    INTERVIEW_INVITE(true, true),
    JOB_ALERT(true, true),
    COMPANY_INVITE(true, true),
    CV_PROCESSED(true, false);

    private final boolean defaultInApp;
    private final boolean defaultEmail;

    NotificationType(boolean defaultInApp, boolean defaultEmail) {
        this.defaultInApp = defaultInApp;
        this.defaultEmail = defaultEmail;
    }

    public boolean defaultInApp() { return defaultInApp; }

    public boolean defaultEmail() { return defaultEmail; }
}
