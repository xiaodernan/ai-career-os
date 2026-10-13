package com.careeros.ai.web;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.MemoryItem;
import com.careeros.ai.dto.UpdateMemoryRequest;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * The browser's surface over the AI service's long-term memory (AGENTS.md §6).
 *
 * The write path for memory has existed since the chat feature — every turn adds facts the
 * model extracted — while nothing could read one back or correct it, so a sentence the
 * extractor got wrong was quoted as fact forever. These three routes close that loop.
 *
 * This controller holds no logic of its own: every route scopes to the caller and forwards.
 * The ownership check lives in the ai-service's `WHERE`, which is why another user's id
 * answers 404 rather than 403 here — "not yours" and "not there" are the same answer.
 */
@RestController
@RequestMapping("/api/v1/memories")
public class MemoryController {

    private final AiServiceClient ai;

    public MemoryController(AiServiceClient ai) {
        this.ai = ai;
    }

    @GetMapping
    public List<MemoryItem> list(@CurrentUser AuthUser user,
                                 @RequestParam(required = false) @Size(max = 16) List<String> kinds) {
        return items(ai.listMemories(kinds, user.id()));
    }

    @PatchMapping("/{id}")
    public ResponseEntity<MemoryItem> patch(@CurrentUser AuthUser user, @PathVariable UUID id,
                                            @RequestBody @Valid UpdateMemoryRequest request) {
        // A UUID path variable, not a String plus a parse: a malformed id is a 400 the
        // framework's own type-mismatch handler writes, not an IllegalArgumentException
        // the catch-all would answer 500 to.
        Map<String, Object> row = ai.patchMemory(id, request.content(), request.importance(), user.id());
        return ResponseEntity.ok(item(row));
    }

    /** 204 whether or not a row went away: the caller asked for it gone and it now is. */
    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        ai.deleteMemory(id, user.id());
    }

    private static List<MemoryItem> items(List<Map<String, Object>> rows) {
        List<MemoryItem> out = new ArrayList<>(rows.size());
        for (Map<String, Object> row : rows) {
            out.add(item(row));
        }
        return out;
    }

    /**
     * Maps the ai-service's camelCase JSON, not a record's components: a missing key is
     * rendered as null rather than throwing, because the page it feeds has to say
     * "no memories" rather than fail on one unexpected shape.
     */
    private static MemoryItem item(Map<String, Object> row) {
        return new MemoryItem(
                str(row.get("id")),
                str(row.get("kind")),
                str(row.get("key")),
                str(row.get("content")),
                num(row.get("importance")),
                str(row.get("source")),
                str(row.get("createdAt")),
                str(row.get("updatedAt")));
    }

    private static String str(Object v) {
        return v == null ? null : String.valueOf(v);
    }

    private static Double num(Object v) {
        return v instanceof Number n ? n.doubleValue() : null;
    }
}
