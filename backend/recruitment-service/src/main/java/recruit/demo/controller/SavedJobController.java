package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.SavedJobDtos.SavedJobResponse;
import recruit.demo.service.SavedJobService;

import java.util.List;

@RestController
@RequestMapping("/api/saved-jobs")
@RequiredArgsConstructor
@PreAuthorize("hasRole('CANDIDATE') or hasAuthority('application:read-own')")
public class SavedJobController {

    private final SavedJobService savedJobService;

    @GetMapping
    public BaseResponse<List<SavedJobResponse>> listMine() {
        return BaseResponse.success(savedJobService.listMine());
    }

    @PostMapping("/{jobId}")
    public BaseResponse<SavedJobResponse> save(@PathVariable Integer jobId) {
        return BaseResponse.success(savedJobService.save(jobId));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> unsave(@PathVariable Integer id) {
        savedJobService.unsave(id);
        return ResponseEntity.noContent().build();
    }
}
