package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * {@link Paging} is the only place a page number becomes a query window, and that only holds
 * while nothing else calls the constructors directly. This walks the shipped sources so a new
 * list endpoint cannot re-open the 500 by writing the obvious-looking {@code PageRequest.of}.
 */
class PagingWiringTest {

    private static final Path MAIN = Path.of("src", "main", "java");

    private static final List<String> FORBIDDEN = List.of(
            "PageRequest.of(", "PageRequest.ofSize(", "Pageable.ofSize(", "Pageable.of(");

    @Test
    void onlyPagingConstructsAWindow() throws IOException {
        Map<String, List<String>> perFile;
        try (Stream<Path> files = Files.walk(MAIN)) {
            perFile = files.filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> !"Paging.java".equals(p.getFileName().toString()))
                    .collect(Collectors.toMap(PagingWiringTest::relative, PagingWiringTest::hits));
        }
        assertThat(perFile).isNotEmpty();
        perFile.forEach((file, hits) -> assertThat(hits)
                .as("%s builds a paging window outside Paging.java", file)
                .isEmpty());
    }

    /** Positive control: the scan reads real file bodies, and Paging.java itself is a hit. */
    @Test
    void theScanActuallySeesTheCallItIsGuarding() throws IOException {
        assertThat(hits(MAIN.resolve("com").resolve("careeros").resolve("common").resolve("Paging.java")))
                .contains("PageRequest.of(");
    }

    @Test
    void noControllerCapsPageSizeByHandAnymore() throws IOException {
        try (Stream<Path> files = Files.walk(MAIN)) {
            List<String> handRolled = files.filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> p.getFileName().toString().endsWith("Controller.java"))
                    .filter(p -> reads(p).contains("Math.min(size"))
                    .map(PagingWiringTest::relative)
                    .toList();
            assertThat(handRolled)
                    .as("the ceiling lives in Paging.MAX_PAGE_SIZE, not in each controller")
                    .isEmpty();
        }
    }

    private static List<String> hits(Path file) {
        String text = reads(file);
        return FORBIDDEN.stream().filter(text::contains).toList();
    }

    private static String reads(Path file) {
        try {
            return Files.readString(file);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String relative(Path file) {
        return MAIN.relativize(file).toString().replace('\\', '/');
    }
}
