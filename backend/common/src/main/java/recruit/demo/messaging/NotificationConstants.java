package recruit.demo.messaging;

/** Hằng số exchange, queue và routing key cho hệ thống thông báo RabbitMQ. */
public final class NotificationConstants {

    private NotificationConstants() {}

    public static final String EXCHANGE = "hirelens.events";
    public static final String DLX = "hirelens.events.dlx";
    public static final String QUEUE = "notification.events";
    public static final String DLQ = "notification.events.dlq";

    public static final String RK_APPLICATION_STATUS_CHANGED = "application.status-changed";
    public static final String RK_CV_PROCESSED = "cv.processed";
    public static final String RK_COMPANY_REVIEWED = "company.reviewed";
    public static final String RK_JOB_LOCKED = "job.locked";
    public static final String RK_JOB_PUBLISHED = "job.published";
    public static final String RK_COMPANY_MEMBER_INVITED = "company.member-invited";
}
