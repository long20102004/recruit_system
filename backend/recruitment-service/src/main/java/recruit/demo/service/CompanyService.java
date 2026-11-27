package recruit.demo.service;

import recruit.demo.dto.FileLinkDto;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.CompanyDtos.*;

import java.util.List;

public interface CompanyService {
    List<CompanyDto> listPublic(String q, String city, String industry, String sort);
    CompanyDto getPublic(Integer id);
    FollowResponse follow(Integer companyId);
    FollowResponse unfollow(Integer companyId);

    RecruiterCompanyProfileDto getMyCompany();
    RecruiterCompanyProfileDto saveDraft(CompanyRegistrationRequest request);
    RecruiterCompanyProfileDto submitRegistration(CompanyRegistrationRequest request);
    RecruiterCompanyProfileDto updateProfile(CompanyProfileUpdateRequest request);
    RecruiterCompanyProfileDto uploadFile(String kind, MultipartFile file);

    List<CompanyDto> listAdmin(String status, String q, String city, String industry);
    CompanyDto getAdmin(Integer id);
    CompanyDto approve(Integer id);
    CompanyDto reject(Integer id, String reason);
    CompanyDto lock(Integer id, String reason);
    CompanyDto unlock(Integer id);
    /** Link ký tạm (inline) tới giấy phép trên R2 cho admin (specs/008-r2-storage). */
    FileLinkDto licenseLink(Integer id);
}
