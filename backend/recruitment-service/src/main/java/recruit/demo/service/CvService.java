package recruit.demo.service;

import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.dto.CvFormResponse;

public interface CvService {
    String FILE_NAME = "file_name";
    String FILE_URL = "file_url";
    String PARSING_STATUS = "parsing_status";
    String PROFILE_JSON = "extracted_profile";

    CvFormResponse mine();
    CandidateProfileDto upload(MultipartFile file);
    CvFormResponse confirm(ConfirmCvRequest request);
}
