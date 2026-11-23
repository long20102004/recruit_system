package recruit.demo.controller;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ServiceDtos.*;
import recruit.demo.entity.User;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.UserRepository;
@RestController
@RequestMapping("/internal/users")
@RequiredArgsConstructor
public class InternalUserController {
    private final UserRepository users;
    @GetMapping("/{id}")
    public UserSnapshot get(@PathVariable Integer id) { return snapshot(require(id)); }
    @PatchMapping("/{id}")
    @Transactional
    public UserSnapshot update(@PathVariable Integer id, @RequestBody ProfileUpdate update) {
        User user = require(id);
        if (update.fullName() != null && !update.fullName().isBlank()) user.setFullName(update.fullName());
        if (update.phone() != null) user.setPhone(update.phone());
        return snapshot(users.save(user));
    }
    private User require(Integer id) { return users.findById(id)
        .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "User not found")); }
    private UserSnapshot snapshot(User u) {
        return new UserSnapshot(u.getId(), u.getFullName(), u.getEmail(), u.getPhone(), u.getRole(), u.getStatus());
    }
}
