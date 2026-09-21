package com.careeros.common;

import java.util.List;
import org.springframework.data.domain.Page;

/** Standard pagination payload: {items,total,page,size}. */
public record PageDTO<T>(List<T> items, long total, int page, int size) {

    public static <T> PageDTO<T> of(List<T> items, long total, int page, int size) {
        return new PageDTO<>(items, total, page, size);
    }

    public static <E, T> PageDTO<T> from(Page<E> page, java.util.function.Function<E, T> mapper) {
        return new PageDTO<>(page.getContent().stream().map(mapper).toList(),
                page.getTotalElements(), page.getNumber(), page.getSize());
    }
}
