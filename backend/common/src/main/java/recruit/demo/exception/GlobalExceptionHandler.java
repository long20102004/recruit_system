package recruit.demo.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import recruit.demo.dto.ErrorResponse;
import recruit.demo.dto.BaseResponse;

import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ErrorResponse> handleApi(ApiException ex) {
        return ResponseEntity.status(ex.getStatus()).body(new ErrorResponse(ex.getMessage()));
    }

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<BaseResponse<Object>> handleBusiness(BusinessException ex) {
        return ResponseEntity.status(resolveHttpStatus(ex.getCode()))
                .body(BaseResponse.builder()
                        .code(ex.getCode())
                        .message(ex.getMessage())
                        .data(ex.getData())
                        .build());
    }

    /** Mã có trong {@link ErrorCode} dùng status gắn sẵn; mã tự do là HTTP status hợp lệ thì giữ nguyên, còn lại 500. */
    static HttpStatus resolveHttpStatus(Long code) {
        ErrorCode known = ErrorCode.fromCode(code);
        if (known != null) return known.getHttpStatus();
        if (code != null && code >= 400 && code < 600) {
            HttpStatus status = HttpStatus.resolve(code.intValue());
            if (status != null) return status;
        }
        return HttpStatus.INTERNAL_SERVER_ERROR;
    }

    @ExceptionHandler(BadCredentialsException.class)
    public ResponseEntity<ErrorResponse> handleBadCredentials(BadCredentialsException ex) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(new ErrorResponse("Invalid email or password"));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ErrorResponse> handleAccessDenied(AccessDeniedException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(new ErrorResponse("Access denied"));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        if (message.isBlank()) {
            message = "Validation failed";
        }
        return ResponseEntity.badRequest().body(new ErrorResponse(message));
    }

    /** JSON sai cú pháp hoặc sai kiểu (vd enum không hợp lệ): 400, không lộ chi tiết parser. */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleUnreadable(HttpMessageNotReadableException ex) {
        return ResponseEntity.badRequest().body(new ErrorResponse("Dữ liệu gửi lên không hợp lệ"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ErrorResponse(ex.getMessage() != null ? ex.getMessage() : "Unexpected error"));
    }
}
