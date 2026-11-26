package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

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

    /** Cắt trang từ danh sách đã có sẵn trong bộ nhớ (vd kết quả matching từ AI service). */
    public static <T> PageResponse<T> of(List<T> all, Pageable pageable) {
        int from = (int) Math.min(pageable.getOffset(), all.size());
        int to = Math.min(from + pageable.getPageSize(), all.size());
        return toPageResponse(new PageImpl<>(all.subList(from, to), pageable, all.size()));
    }

    /** Như {@link #toPageResponse(Page)} nhưng đổi từng phần tử (vd entity sang DTO). */
    public static <E, T> PageResponse<T> toPageResponse(Page<E> page, Function<? super E, ? extends T> mapper) {
        return toPageResponse(page.map(mapper::apply));
    }
}
