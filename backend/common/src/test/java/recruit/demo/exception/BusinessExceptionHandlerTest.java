package recruit.demo.exception;

import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.PageResponse;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class BusinessExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void errorCodeUsesItsHttpStatusAndBody() {
        var res = handler.handleBusiness(new BusinessException(ErrorCode.CV_NO_TEXT, Map.of("file", "a.pdf")));
        assertThat(res.getStatusCode()).isEqualTo(HttpStatus.UNPROCESSABLE_ENTITY);
        BaseResponse<Object> body = res.getBody();
        assertThat(body).isNotNull();
        assertThat(body.getCode()).isEqualTo(3003L);
        assertThat(body.getMessage()).isEqualTo(ErrorCode.CV_NO_TEXT.getMessage());
        assertThat(body.getData()).isEqualTo(Map.of("file", "a.pdf"));
    }

    @Test
    void freeHttpCodeIsKeptAndUnknownCodeIs500() {
        assertThat(GlobalExceptionHandler.resolveHttpStatus(409L)).isEqualTo(HttpStatus.CONFLICT);
        assertThat(GlobalExceptionHandler.resolveHttpStatus(418L)).isEqualTo(HttpStatus.I_AM_A_TEAPOT);
        assertThat(GlobalExceptionHandler.resolveHttpStatus(9999L)).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(GlobalExceptionHandler.resolveHttpStatus(null)).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(new BusinessException("boom").getCode()).isEqualTo(500L);
    }

    @Test
    void successAndPageResponses() {
        BaseResponse<String> ok = BaseResponse.success("x");
        assertThat(ok.getCode()).isEqualTo(200L);
        assertThat(ok.getMessage()).isEqualTo("Success");

        var page = new PageImpl<>(List.of(1, 2, 3), PageRequest.of(1, 3), 7);
        PageResponse<String> mapped = PageResponse.toPageResponse(page, i -> "#" + i);
        assertThat(mapped.getContent()).containsExactly("#1", "#2", "#3");
        assertThat(mapped.getPageNumber()).isEqualTo(1);
        assertThat(mapped.getTotalElements()).isEqualTo(7);
        assertThat(mapped.getTotalPages()).isEqualTo(3);
        assertThat(mapped.isLast()).isFalse();
    }
}
