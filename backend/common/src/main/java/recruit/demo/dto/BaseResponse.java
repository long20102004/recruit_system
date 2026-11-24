package recruit.demo.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import recruit.demo.exception.ErrorCode;

/**
 * Khung response chung: {@code {"code": 200, "message": "Success", "data": ...}}.
 * Trường null bị bỏ khỏi JSON. Frontend đọc lỗi qua {@code message}, giống {@code ErrorResponse}.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class BaseResponse<T> {
    private String message;
    private Long code;
    private T data;

    public static <T> BaseResponse<T> success(T data) {
        return BaseResponse.<T>builder()
                .message(ErrorCode.SUCCESS.getMessage())
                .code((long) ErrorCode.SUCCESS.getCode())
                .data(data)
                .build();
    }

    public static <T> BaseResponse<T> success(String message, Long code) {
        return BaseResponse.<T>builder().message(message).code(code).build();
    }

    public static BaseResponse<Void> error(Long code, String message) {
        return BaseResponse.<Void>builder().code(code).message(message).build();
    }

    public static BaseResponse<Void> error(ErrorCode errorCode) {
        return error((long) errorCode.getCode(), errorCode.getMessage());
    }
}
