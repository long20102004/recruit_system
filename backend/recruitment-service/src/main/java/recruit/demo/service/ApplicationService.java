package recruit.demo.service;

import java.util.List;
import recruit.demo.dto.ApplicationDtos;

public interface ApplicationService {
    ApplicationDtos.ApplicationResponse apply(Integer jobId, ApplicationDtos.ApplyRequest request);
    List<ApplicationDtos.ApplicationResponse> myApplications();
    List<ApplicationDtos.ApplicationResponse> recruiterApplications();
}
