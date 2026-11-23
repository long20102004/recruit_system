package recruit.demo.service.cvmatch;

import org.junit.jupiter.api.Test;
import recruit.demo.client.CvMatchApi;
import recruit.demo.client.HttpCvMatchClient;
import recruit.demo.entity.JobStatus;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/**
 * Hop dong voi cvmatch THAT (chi chay khi dat CVMATCH_IT_URL, vd http://127.0.0.1:8013; token: CVMATCH_IT_TOKEN).
 * DB cvmatch nen la DB rieng cho lan thu: test them CV / JD.
 */
class CvMatchLiveContractTest {

    @Test
    @SuppressWarnings("unchecked")
    void payloadsAreAcceptedAndMatchReturnsDetail() {
        String url = System.getenv("CVMATCH_IT_URL");
        assumeTrue(url != null && !url.isBlank(), "dat CVMATCH_IT_URL de chay");
        ObjectMapper mapper = new ObjectMapper();
        CvMatchApi api = new HttpCvMatchClient(mapper, url, Objects.toString(System.getenv("CVMATCH_IT_TOKEN"), ""), 60000);
        assertEquals(200, api.health().status());

        String run = Long.toString(System.nanoTime(), 36);
        Map<String, Object> extracted = mapper.readValue("""
            {"personal_info":{"full_name":"Gia Lap","email":"cv@x.test","phone":null,"github_url":null},
             "objective":"Backend developer Java",
             "education":[{"school":"Dai hoc Bach khoa","major":"Khoa hoc may tinh","start_year":"2015","end_year":"2019","gpa":null}],
             "experience":[{"company":"Cong ty A","job_title":"Backend Developer","start_date":"03/2022","end_date":null,
                            "description":["Thiet ke REST API bang Spring Boot cho he thong thanh toan",
                                           "Toi uu truy van PostgreSQL"]}],
             "personal_projects":[],"skills":["Java","Spring Boot","PostgreSQL"],"certificates":[],"honours":[],
             "languages":[],"implied_skills":[{"name":"JVM"}]}
            """, Map.class);
        var cv = CvMatchPayloads.cvPayload(extracted, Map.of("Kỹ năng", List.of("Java, Spring Boot, PostgreSQL, Docker")),
                "it-" + run + "@x.test", "Hà Nội");
        var r = api.postCv(cv);
        assertEquals(200, r.status(), r.detail());
        assertEquals("ok", r.body().path("status").asString());
        String cvId = r.body().path("cv_id").asString();

        int jobId = 900000 + (int) (System.nanoTime() % 99999);
        var jd = new LinkedHashMap<>(CvMatchPayloads.jdPayload(jobId, "Java Backend Developer", null, "Hà Nội", "Full-time",
                BigDecimal.ONE, "Phat trien API bang Spring Boot\nToi uu co so du lieu", "Thanh thao Java", null,
                List.of(new CvMatchPayloads.JobSkillItem("Java", true), new CvMatchPayloads.JobSkillItem("Spring Boot", true))));
        jd.put("status", CvMatchPayloads.jdStatus(JobStatus.PUBLISHED));
        var j = api.postJd(jd);
        assertEquals(200, j.status(), j.detail());

        var m = api.matchJd(CvMatchPayloads.jdId(jobId), Map.of("include_cv_ids", List.of(cvId), "N", 1));
        assertEquals(200, m.status(), m.detail());
        var item = m.body().path("items").get(0);
        assertEquals(cvId, item.path("cv_id").asString());
        assertTrue(item.path("features").path("A1").isNumber());
        assertTrue(item.path("skills").path("met").isArray());
        var e = api.explainForHr(m.body().path("run_id").asString(), cvId);
        assertEquals(200, e.status(), e.detail());

        assertEquals(200, api.patchJdStatus(CvMatchPayloads.jdId(jobId), "closed").status());
        assertEquals(200, api.deleteCv(cvId).status());
    }
}
