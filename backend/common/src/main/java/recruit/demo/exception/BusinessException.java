package recruit.demo.exception;

import lombok.Getter;

/**
 * Lỗi nghiệp vụ mang mã {@link ErrorCode} (hoặc mã tự do) và dữ liệu kèm theo.
 * {@link GlobalExceptionHandler} trả về dạng {@code BaseResponse}.
 */
@Getter
public class BusinessException extends RuntimeException {
    private final Long code;
    private final String message;
    private final transient Object data;
    private final String errorCodeTracing;

    public BusinessException(String message) {
        this((long) ErrorCode.INTERNAL_ERROR.getCode(), message, null, null);
    }

    public BusinessException(Long code, String message) {
        this(code, message, null, null);
    }

    public BusinessException(Long code, String message, Object data) {
        this(code, message, data, null);
    }

    public BusinessException(Long code, String message, Object data, String errorCodeTracing) {
        super(message);
        this.code = code;
        this.message = message;
        this.data = data;
        this.errorCodeTracing = errorCodeTracing;
    }

    public BusinessException(ErrorCode errorCode) {
        this(errorCode, errorCode.getMessage(), null);
    }

    public BusinessException(ErrorCode errorCode, Object data) {
        this(errorCode, errorCode.getMessage(), data);
    }

    /** Dùng mã của errorCode nhưng thay câu thông báo (vd thêm chi tiết). */
    public BusinessException(ErrorCode errorCode, String message, Object data) {
        this((long) errorCode.getCode(), message, data, null);
    }
}
