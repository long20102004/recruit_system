package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.domain.Page;

import java.util.List;
import java.util.function.Function;

/** Một trang dữ liệu, tách khỏi {@link Page} của Spring Data để JSON ổn định. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PageResponse<T> {
    private List<T> content;
    private int pageNumber;
    private int pageSize;
    private long totalElements;
    private int totalPages;
    private boolean last;

    public static <T> PageResponse<T> toPageResponse(Page<T> page) {
        return PageResponse.<T>builder()
                .content(page.getContent())
                .pageNumber(page.getNumber())
                .pageSize(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .last(page.isLast())
                .build();
    }

    /** Như {@link #toPageResponse(Page)} nhưng đổi từng phần tử (vd entity sang DTO). */
    public static <E, T> PageResponse<T> toPageResponse(Page<E> page, Function<? super E, ? extends T> mapper) {
        return toPageResponse(page.map(mapper::apply));
    }
}
