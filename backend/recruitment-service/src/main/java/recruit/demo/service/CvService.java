package recruit.demo.service;

import recruit.demo.dto.FileLinkDto;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.dto.CvDocumentDtos.CvDocumentDto;
import recruit.demo.dto.CvDocumentDtos.CvUploadResponse;
import recruit.demo.dto.CvFormResponse;
import recruit.demo.dto.CvTemplateSelectionDtos.CvPreviewRequest;
import recruit.demo.dto.CvTemplateSelectionDtos.CvPreviewResult;

import java.util.List;

/** CV của ứng viên. Tham số cvId = null nghĩa là CV chính (giữ tương thích API cũ một CV). */
public interface CvService {
    String FILE_NAME = "file_name";
    String FILE_URL = "file_url";
    String PARSING_STATUS = "parsing_status";
    String PROFILE_JSON = "extracted_profile";
    String SKILLS = "Kỹ năng";
    int MAX_CVS = 5;

    CvFormResponse mine(Integer cvId);

    /** API cũ: xoá CV chính rồi trả form của CV chính mới (hoặc form trống). */
    CvFormResponse remove();

    /** API cũ: ghi vào CV chính, chưa có CV thì tạo CV đầu tiên. */
    CandidateProfileDto upload(MultipartFile file);

    CvUploadResponse uploadNew(MultipartFile file, String title);

    CvUploadResponse reupload(Integer cvId, MultipartFile file);

    CvFormResponse confirm(Integer cvId, ConfirmCvRequest request);

    List<CvDocumentDto> documents();

    /** Tạo CV trống (không file) cho nút Tạo CV từ đầu ở C04. */
    CvDocumentDto createBlank(String title);

    CvDocumentDto createBlank(String title, Integer templateId);

    CvDocumentDto setTemplate(Integer cvId, Integer templateId);

    CvPreviewResult preview(CvPreviewRequest request);

    FileLinkDto generatePdf(Integer cvId);

    CvDocumentDto rename(Integer cvId, String title);

    List<CvDocumentDto> setMain(Integer cvId);

    void delete(Integer cvId);

    FileLinkDto file(Integer cvId);
}
