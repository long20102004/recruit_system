package recruit.demo.dto;

import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.util.List;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;

class PagingTest {

    @Test
    void pagingOfClampsPageAndSize() {
        Pageable negPage = Paging.of(-3, 20);
        assertThat(negPage.getPageNumber()).isZero();
        assertThat(negPage.getPageSize()).isEqualTo(20);

        Pageable zeroSize = Paging.of(0, 0);
        assertThat(zeroSize.getPageNumber()).isZero();
        assertThat(zeroSize.getPageSize()).isEqualTo(1);

        Pageable hugeSize = Paging.of(1, 500);
        assertThat(hugeSize.getPageNumber()).isEqualTo(1);
        assertThat(hugeSize.getPageSize()).isEqualTo(Paging.MAX_SIZE);

        Pageable normal = Paging.of(2, 20);
        assertThat(normal.getPageNumber()).isEqualTo(2);
        assertThat(normal.getPageSize()).isEqualTo(20);
    }

    @Test
    void pageResponseOfSlicesInMemoryList() {
        List<Integer> all = IntStream.range(0, 45).boxed().toList();

        PageResponse<Integer> middle = PageResponse.of(all, PageRequest.of(1, 20));
        assertThat(middle.getContent()).containsExactlyElementsOf(IntStream.range(20, 40).boxed().toList());
        assertThat(middle.getTotalElements()).isEqualTo(45);
        assertThat(middle.getTotalPages()).isEqualTo(3);
        assertThat(middle.isLast()).isFalse();
        assertThat(middle.getPageNumber()).isEqualTo(1);

        PageResponse<Integer> last = PageResponse.of(all, PageRequest.of(2, 20));
        assertThat(last.getContent()).hasSize(5).containsExactly(40, 41, 42, 43, 44);
        assertThat(last.isLast()).isTrue();

        PageResponse<Integer> beyond = PageResponse.of(all, PageRequest.of(5, 20));
        assertThat(beyond.getContent()).isEmpty();
        assertThat(beyond.getTotalElements()).isEqualTo(45);

        PageResponse<Integer> empty = PageResponse.of(List.of(), PageRequest.of(0, 20));
        assertThat(empty.getContent()).isEmpty();
        assertThat(empty.getTotalPages()).isZero();
    }
}
