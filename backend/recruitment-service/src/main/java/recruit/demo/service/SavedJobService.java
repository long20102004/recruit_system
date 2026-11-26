package recruit.demo.service;

import recruit.demo.dto.SavedJobDtos.SavedJobResponse;

import java.util.List;

public interface SavedJobService {
    List<SavedJobResponse> listMine();
    SavedJobResponse save(Integer jobId);
    void unsave(Integer jobIdOrSavedId);
}
