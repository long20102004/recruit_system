package recruit.demo.client;

import tools.jackson.databind.JsonNode;

import java.util.Map;

/**
 * API cua module match cvmatch (services/cvmatch-ai, hop dong: services/cvmatch-ai/openapi.json). Moi ham tra ve ma HTTP + body;
 * loi ket noi / het thoi gian -> {@link CvMatchUnavailableException}. Diem quyet dinh 4xx/5xx de ben goi.
 */
public interface CvMatchApi {

    Response postCv(Map<String, Object> cv);

    Response deleteCv(String cvId);

    Response postJd(Map<String, Object> jd);

    Response patchJdStatus(String jdId, String status);

    /** Luong C: JD -> top N CV. body: K, N, include_cv_ids, exclude_cv_ids, hard_filters... */
    Response matchJd(String jdId, Map<String, Object> body);

    /** Luong D: CV -> top N JD dang mo. body: N, include_jd_ids, exclude_jd_ids... */
    Response matchCv(String cvId, Map<String, Object> body);

    /** Giai thich cho HR (co diem so). */
    Response explainForHr(String runId, String cvId);

    /** Giai thich huong ung vien (khong diem so). */
    Response explainForCandidate(String runId, String jdId);

    Response health();

    record Response(int status, JsonNode body) {
        public boolean ok() {
            return status >= 200 && status < 300;
        }

        public String detail() {
            if (body == null) return "HTTP " + status;
            JsonNode d = body.path("detail");
            return "HTTP " + status + (d.isMissingNode() || d.isNull() ? "" : ": " + d);
        }
    }

    class CvMatchUnavailableException extends RuntimeException {
        public CvMatchUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
