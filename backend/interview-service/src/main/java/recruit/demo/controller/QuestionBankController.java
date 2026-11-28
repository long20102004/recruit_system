package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.dto.QuestionBankDtos.*;
import recruit.demo.service.QuestionBankService;

@RestController
@RequestMapping("/api/interviews/admin/questions")
@PreAuthorize("hasRole('ADMIN')")
@RequiredArgsConstructor
public class QuestionBankController {
    private final QuestionBankService bank;

    @GetMapping
    public PageResponse<Question> list(@RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "100") int size) {
        return bank.list(Paging.of(page, size));
    }

    @PostMapping
    public Question create(@Valid @RequestBody Input input) {
        return bank.save(null, input);
    }

    @PutMapping("/{id}")
    public Question update(@PathVariable Integer id, @Valid @RequestBody Input input) {
        return bank.save(id, input);
    }

    @PatchMapping("/{id}")
    public Question changeState(@PathVariable Integer id, @RequestBody State state) {
        return bank.changeState(id, state);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void archive(@PathVariable Integer id) {
        bank.archive(id);
    }
}
