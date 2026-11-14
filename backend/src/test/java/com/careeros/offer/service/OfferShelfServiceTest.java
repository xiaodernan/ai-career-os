package com.careeros.offer.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.common.ApiException;
import com.careeros.offer.dto.OfferShelfDtos.OfferItem;
import com.careeros.offer.dto.OfferShelfDtos.OfferShelfResponse;
import com.careeros.offer.dto.OfferShelfDtos.UpsertOfferRequest;
import com.careeros.offer.entity.OfferRow;
import com.careeros.offer.repository.OfferShelfRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * The shelf's own rules: the owner scope (a row another reader sent is a 404, not a
 * leak), the order (the expiring row first, undated rows trail), and the total the
 * reader compares by. The repository is stubbed; what this class owns is the shape
 * the compare view consumes.
 */
class OfferShelfServiceTest {

    private final UUID userId = UUID.randomUUID();
    private final OfferShelfRepository repository = mock(OfferShelfRepository.class);
    private final OfferShelfService service = new OfferShelfService(repository);

    private UpsertOfferRequest request(String label, int base, int bonus, int equity) {
        return new UpsertOfferRequest(label, base, bonus, equity, "USD", "hybrid", null, null, null);
    }

    private OfferRow row(UUID id, String label, int base, int bonus, int equity,
                         OffsetDateTime deadline) {
        OfferRow row = new OfferRow();
        row.setUserId(userId);
        row.setId(id);
        row.setLabel(label);
        row.setBase(base);
        row.setBonus(bonus);
        row.setEquity(equity);
        row.setCurrency("USD");
        row.setRemoteType("hybrid");
        row.setDeadline(deadline);
        row.setCreatedAt(OffsetDateTime.now());
        row.setUpdatedAt(OffsetDateTime.now());
        return row;
    }

    @Test
    void createDefaultsTheDecisionToPending_andAnExplicitDecisionStages() {
        when(repository.save(any())).thenAnswer(inv -> {
            OfferRow row = inv.getArgument(0);
            row.setId(UUID.randomUUID());
            if (row.getCreatedAt() == null) row.setCreatedAt(OffsetDateTime.now());
            if (row.getUpdatedAt() == null) row.setUpdatedAt(OffsetDateTime.now());
            return row;
        });

        UpsertOfferRequest blank = new UpsertOfferRequest(
                "Initech", 150000, 0, 0, "USD", "hybrid", null, null, null);
        ArgumentCaptor<OfferRow> captor = ArgumentCaptor.forClass(OfferRow.class);
        OfferItem item = service.create(userId, blank);

        org.mockito.Mockito.verify(repository).save(captor.capture());
        assertThat(captor.getValue().getDecision()).isEqualTo("pending");
        assertThat(item.decision()).isEqualTo("pending");

        UpsertOfferRequest accepted = new UpsertOfferRequest(
                "Initech", 150000, 0, 0, "USD", "hybrid", null, null, "accepted");
        OfferItem acceptedItem = service.create(userId, accepted);
        assertThat(acceptedItem.decision()).isEqualTo("accepted");
    }

    @Test
    void theShelfOrdersByDeadlineFirst_undatedRowsTrail() {
        UUID datedId = UUID.randomUUID();
        UUID undatedId = UUID.randomUUID();
        when(repository.shelfOrder(userId)).thenReturn(List.of(
                row(datedId, "Acme", 180000, 10000, 20000, OffsetDateTime.now().plusDays(7)),
                row(undatedId, "Globex", 170000, 0, 0, null)));

        OfferShelfResponse response = service.list(userId);

        assertThat(response.items()).extracting(OfferItem::id)
                .containsExactly(datedId, undatedId);
        assertThat(response.items().get(0).totalComp()).isEqualTo(210000);
        assertThat(response.total()).isEqualTo(2);
    }

    @Test
    void aRowAnotherReaderSentIsA404_notALeak() {
        when(repository.findByIdAndUserId(any(), eq(userId))).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.update(userId, UUID.randomUUID(),
                request("X", 1, 0, 0)))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("No such offer");
        assertThatThrownBy(() -> service.delete(userId, UUID.randomUUID()))
                .isInstanceOf(ApiException.class);
    }

    @Test
    void createStampsTheVocabularyDefaultsAndSumsTheTotal() {
        when(repository.save(any())).thenAnswer(inv -> {
            OfferRow row = inv.getArgument(0);
            row.setId(UUID.randomUUID());
            return row;
        });

        UpsertOfferRequest blank = new UpsertOfferRequest(
                "Initech", 150000, 0, 0, null, null, null, null, null);
        ArgumentCaptor<OfferRow> captor = ArgumentCaptor.forClass(OfferRow.class);
        OfferItem item = service.create(userId, blank);

        org.mockito.Mockito.verify(repository).save(captor.capture());
        assertThat(captor.getValue().getCurrency()).isEqualTo("USD");
        assertThat(captor.getValue().getRemoteType()).isEqualTo("onsite");
        assertThat(item.totalComp()).isEqualTo(150000);
    }
}
