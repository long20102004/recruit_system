package recruit.demo.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * Mã lỗi nghiệp vụ dùng chung. Mỗi mã gắn sẵn HTTP status trả về.
 * Dải mã: 1xxx validation, 2xxx identity, 3xxx CV / trích xuất, 4xxx việc làm & matching, 5xxx phỏng vấn.
 */
@Getter
public enum ErrorCode {
    // ── HTTP chuẩn ──────────────────────────────────────
    SUCCESS(200, "Success", HttpStatus.OK),
    BAD_REQUEST(400, "Bad request", HttpStatus.BAD_REQUEST),
    UNAUTHORIZED(401, "Unauthorized", HttpStatus.UNAUTHORIZED),
    FORBIDDEN(403, "Forbidden", HttpStatus.FORBIDDEN),
    NOT_FOUND(404, "Resource not found", HttpStatus.NOT_FOUND),
    CONFLICT(409, "Resource conflict", HttpStatus.CONFLICT),
    INTERNAL_ERROR(500, "Internal server error", HttpStatus.INTERNAL_SERVER_ERROR),
    SERVICE_UNAVAILABLE(503, "Service unavailable", HttpStatus.SERVICE_UNAVAILABLE),

    // ── Validation (1xxx) ────────────────────────────────
    INVALID_INPUT(1001, "Invalid input data", HttpStatus.BAD_REQUEST),
    NULL_VALUE(1002, "Required field is null or empty", HttpStatus.BAD_REQUEST),
    INVALID_FORMAT(1003, "Invalid data format", HttpStatus.BAD_REQUEST),

    // ── Identity (2xxx) ──────────────────────────────────
    INVALID_CREDENTIALS(2001, "Invalid email or password", HttpStatus.UNAUTHORIZED),
    EMAIL_ALREADY_EXISTS(2002, "Email already exists", HttpStatus.CONFLICT),

    // ── CV / trích xuất (3xxx) ───────────────────────────
    CV_FILE_REQUIRED(3001, "File is required", HttpStatus.BAD_REQUEST),
    CV_INVALID_FORMAT(3002, "Chỉ nhận file PDF", HttpStatus.BAD_REQUEST),
    CV_NO_TEXT(3003, "PDF has no readable text; OCR is required for scanned CVs", HttpStatus.UNPROCESSABLE_ENTITY),
    CV_TOO_LARGE(3004, "CV exceeds model context", HttpStatus.PAYLOAD_TOO_LARGE),
    CV_EXTRACTION_FAILED(3005, "Extraction service returned no profile", HttpStatus.BAD_GATEWAY),
    CV_EXTRACTION_UNAVAILABLE(3006, "AI service unavailable; check model and service URL", HttpStatus.SERVICE_UNAVAILABLE),

    // ── Việc làm & matching (4xxx) ───────────────────────
    JOB_NOT_FOUND(4001, "Job not found", HttpStatus.NOT_FOUND),
    MATCHING_UNAVAILABLE(4002, "Matching service unavailable", HttpStatus.SERVICE_UNAVAILABLE),

    // ── Phỏng vấn (5xxx) ─────────────────────────────────
    INTERVIEW_NOT_FOUND(5001, "Interview session not found", HttpStatus.NOT_FOUND);

    private final int code;
    private final String message;
    private final HttpStatus httpStatus;

    ErrorCode(int code, String message, HttpStatus httpStatus) {
        this.code = code;
        this.message = message;
        this.httpStatus = httpStatus;
    }

    /** Tìm theo mã; không có thì null. */
    public static ErrorCode fromCode(Long code) {
        if (code == null) return null;
        for (ErrorCode value : values()) {
            if (value.code == code) return value;
        }
        return null;
    }
}
