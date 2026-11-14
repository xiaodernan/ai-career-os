package com.careeros.application.web;

import com.careeros.application.dto.ApplicationDtos.LetterCatalogItem;
import com.careeros.application.service.ApplicationLetterService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The whole kept shelf in one room.
 *
 * <p>Every cover letter the reader has chosen to keep, across every application they hold, newest
 * first, with the title of the application it hangs off. The endpoint exists because letters used to
 * live inside one dialog per application, and a reader who wanted their best line back for the next
 * posting had to open seven boards to find it. Nothing is synthesized here and nothing is
 * searchable yet — the search already reaches the letter bodies through the palette; this is the
 * plain indexed listing the ink desk needs to be one gallery instead of seven drawers.
 *
 * <p>Capped at 200 rows by the repository: the ledger this serves was designed at letters-per-
 * application scale; if a reader keeps 200 cover letters, the shelf stops being a list and starts
 * being a filing cabinet, at which point the answer is a pager, not more bytes.
 */
@RestController
@RequestMapping("/api/v1")
public class LetterFileController {

    private final ApplicationLetterService letters;

    public LetterFileController(ApplicationLetterService letters) {
        this.letters = letters;
    }

    @GetMapping("/letters")
    public LetterFile catalog(@CurrentUser AuthUser user) {
        List<LetterCatalogItem> items = letters.catalog(user.id());
        return new LetterFile(items, items.size());
    }

    /** The gallery's answer key: one call, every letter, with the application titles inline. */
    public record LetterFile(List<LetterCatalogItem> items, int total) {
    }
}
