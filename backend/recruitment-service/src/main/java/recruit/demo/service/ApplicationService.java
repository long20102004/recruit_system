package recruit.demo.service;

import org.springframework.core.io.Resource;
import org.springframework.data.domain.Pageable;
import recruit.demo.dto.ApplicationDtos.*;
import recruit.demo.dto.PageResponse;

import java.util.List;

public interface ApplicationService {
    ApplicationResponse apply(Integer jobId, ApplyRequest request);
    PageResponse<ApplicationResponse> myApplications(Pageable pageable);
    PageResponse<ApplicationResponse> recruiterApplications(Pageable pageable);
    PageResponse<ApplicationResponse> recruiterApplications(String status, Integer jobId, Integer minMatchScore, Pageable pageable);

    ApplicationDetailResponse getDetail(Integer id);
    ApplicationDetailResponse updateStatus(Integer id, String statusRaw, String note);
    List<ApplicationResponse> bulkUpdateStatus(List<Integer> applicationIds, String statusRaw, String note);
    ApplicationDetailResponse withdraw(Integer id);
    ApplicationDetailResponse saveNote(Integer id, int rating, String internalNote);
    List<ApplicationHistoryDto> history(Integer id);
    Resource loadCvFile(Integer id);
}
