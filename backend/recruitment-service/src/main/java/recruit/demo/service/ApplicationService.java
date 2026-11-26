package recruit.demo.service;

import org.springframework.data.domain.Pageable;
import recruit.demo.dto.ApplicationDtos;
import recruit.demo.dto.PageResponse;

public interface ApplicationService {
    ApplicationDtos.ApplicationResponse apply(Integer jobId, ApplicationDtos.ApplyRequest request);
    PageResponse<ApplicationDtos.ApplicationResponse> myApplications(Pageable pageable);
    PageResponse<ApplicationDtos.ApplicationResponse> recruiterApplications(Pageable pageable);
}
