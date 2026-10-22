package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

/**
 * The one funnel every list endpoint answers through: {@code List.of(...)} mapped
 * rows plus the Spring {@code Page}'s own coordinates, eight call sites in main and
 * no test until this file. The trap the mapping holds is which number is which:
 * {@code total} is the count ACROSS pages (the frontend's pager divides it by size),
 * {@code page} is the request's page (which stays what was asked even when the page
 * came back empty — the past-the-end case the pager corrects from), and {@code size}
 * is the clamped window. A mapping that swapped total for content-size would give
 * every pager in the product one page and a lie about the rest.
 */
class PageDTOTest {

    private PageImpl<String> page(int number, int size, List<String> content, long total) {
        return new PageImpl<>(content, PageRequest.of(number, size), total);
    }

    @Test
    void contentIsMappedAndTheSpringCoordinatesComeAlong() {
        var dto = PageDTO.from(page(1, 2, List.of("a", "b"), 5), String::toUpperCase);

        assertThat(dto.items()).containsExactly("A", "B");
        assertThat(dto.total()).isEqualTo(5);           // across pages, not this page's rows
        assertThat(dto.page()).isEqualTo(1);
        assertThat(dto.size()).isEqualTo(2);
    }

    @Test
    void anEmptyPageStillAnswersItsRequestedCoordinates() {
        // The past-the-end case: the pager needs page=7 and total=100 to correct
        // itself, not zeros — a zeroed envelope would read as "no rows anywhere".
        var dto = PageDTO.from(page(7, 100, List.of(), 100), s -> s);

        assertThat(dto.items()).isEmpty();
        assertThat(dto.page()).isEqualTo(7);
        assertThat(dto.size()).isEqualTo(100);
        assertThat(dto.total()).isEqualTo(100);
    }

    @Test
    void theCoordinatesAreReadFromThePageNotFromTheMappedList() {
        // The trap this pins: `size` is the requested window (25), not how many rows
        // this page happened to carry (3). A pager computing its page count from
        // items.size() would see "3 rows of 3" and print one page for everything.
        var dto = PageDTO.from(page(0, 25, List.of("x", "y", "z"), 3), s -> "mapped:" + s);

        assertThat(dto.items()).containsExactly("mapped:x", "mapped:y", "mapped:z");
        assertThat(dto.items()).hasSize(3);
        assertThat(dto.size()).isEqualTo(25).isNotEqualTo(dto.items().size());
        assertThat(dto.total()).isEqualTo(3L);
    }

    @Test
    void theDirectFactoryCarriesWhatItIsGiven() {
        var dto = PageDTO.of(List.of(1, 2), 2, 0, 10);
        assertThat(dto.items()).containsExactly(1, 2);
        assertThat(dto.total()).isEqualTo(2L);
        assertThat(dto.page()).isZero();
        assertThat(dto.size()).isEqualTo(10);
    }
}
