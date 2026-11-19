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
    private final com.careeros.ai.AiServiceClient ai = mock(com.careeros.ai.AiServiceClient.class);
    private final OfferShelfService service = new OfferShelfService(repository, ai);

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
    void theDecisionLetterShipsTheOfferAndTheShelfSiblingsInOneCall() {
        UUID rowId = UUID.randomUUID();
        OfferRow main = row(rowId, "Main Offer", 280000, 40000, 60000, null);
        main.setDecision("declined");
        OfferRow sib = row(UUID.randomUUID(), "Sibling", 360000, 0, 0, null);
        when(repository.findByIdAndUserId(org.mockito.ArgumentMatchers.eq(rowId),
                org.mockito.ArgumentMatchers.eq(userId)))
                .thenReturn(Optional.of(main));
        when(repository.shelfOrder(userId)).thenReturn(List.of(main, sib));
        when(ai.offerDecisionLetter(org.mockito.ArgumentMatchers.eq(userId), any(), any(), any()))
                .thenReturn(java.util.Map.of("letter",
                        "You passed on it and kept your bar."));

        String out = service.letter(userId, rowId, "en");

        assertThat(out).isEqualTo("You passed on it and kept your bar.");
        ArgumentCaptor<java.util.Map<String, Object>> offerCap =
                ArgumentCaptor.forClass(java.util.Map.class);
        ArgumentCaptor<List<java.util.Map<String, Object>>> sibCap =
                ArgumentCaptor.forClass(List.class);
        org.mockito.Mockito.verify(ai).offerDecisionLetter(
                org.mockito.ArgumentMatchers.eq(userId), offerCap.capture(),
                sibCap.capture(), org.mockito.ArgumentMatchers.eq("en"));
        assertThat(offerCap.getValue())
                .containsEntry("label", "Main Offer")
                .containsEntry("decision", "declined")
                .containsEntry("totalComp", 380000);
        assertThat(sibCap.getValue()).extracting("label").containsExactly("Sibling");
    }

    @Test
    void theStalledOfferLetterSendsTheOfferToTheProviderAndPassesTheAnswerThrough() {
        UUID rowId = UUID.randomUUID();
        OfferRow main = row(rowId, "Main Offer", 280000, 40000, 60000,
                OffsetDateTime.now().minusDays(30));
        when(repository.findByIdAndUserId(org.mockito.ArgumentMatchers.eq(rowId),
                org.mockito.ArgumentMatchers.eq(userId)))
                .thenReturn(Optional.of(main));
        when(ai.followUpLetter(org.mockito.ArgumentMatchers.eq(userId), any(), any()))
                .thenReturn(java.util.Map.of("letter",
                        "Hello — following up on the offer; total was 380000."));

        String out = service.followUpLetter(userId, rowId, "en");

        assertThat(out).isEqualTo("Hello — following up on the offer; total was 380000.");

        assertThatThrownBy(() -> service.followUpLetter(userId, UUID.randomUUID(), "en"))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("No such offer");

        ArgumentCaptor<java.util.Map<String, Object>> offerCap =
                ArgumentCaptor.forClass(java.util.Map.class);
        org.mockito.Mockito.verify(ai).followUpLetter(
                org.mockito.ArgumentMatchers.eq(userId), offerCap.capture(),
                org.mockito.ArgumentMatchers.eq("en"));
        assertThat(offerCap.getValue())
                .containsEntry("label", "Main Offer")
                .containsEntry("totalComp", 380000);
    }

    @Test
    void theCounterLetterShipsTheOfferAndTheSiblingBand_andAnotherAccountGetsA404() {
        UUID rowId = UUID.randomUUID();
        UUID sibId = UUID.randomUUID();
        OfferRow main = row(rowId, "Main Offer", 280000, 40000, 60000, null);
        OfferRow sib = row(sibId, "Sibling", 360000, 0, 0, null);
        when(repository.findByIdAndUserId(org.mockito.ArgumentMatchers.eq(rowId),
                org.mockito.ArgumentMatchers.eq(userId)))
                .thenReturn(Optional.of(main));
        when(repository.findByIdAndUserId(org.mockito.ArgumentMatchers.eq(UUID.randomUUID()),
                org.mockito.ArgumentMatchers.eq(userId)))
                .thenReturn(Optional.empty());
        when(repository.shelfOrder(userId)).thenReturn(List.of(main, sib));
        when(ai.counterOfferLetter(org.mockito.ArgumentMatchers.eq(userId), any(), any(), any()))
                .thenReturn(java.util.Map.of("letter", "The offer is real — the band wants in."));

        String out = service.counterLetter(userId, rowId, "en");

        assertThat(out).isEqualTo("The offer is real — the band wants in.");
        ArgumentCaptor<java.util.Map<String, Object>> offerCap =
                ArgumentCaptor.forClass(java.util.Map.class);
        ArgumentCaptor<List<java.util.Map<String, Object>>> sibCap =
                ArgumentCaptor.forClass(List.class);
        org.mockito.Mockito.verify(ai).counterOfferLetter(
                org.mockito.ArgumentMatchers.eq(userId), offerCap.capture(),
                sibCap.capture(), org.mockito.ArgumentMatchers.eq("en"));
        assertThat(offerCap.getValue())
                .containsEntry("label", "Main Offer")
                .containsEntry("totalComp", 380000);
        assertThat(sibCap.getValue()).extracting("label").containsExactly("Sibling");

        assertThatThrownBy(() -> service.counterLetter(userId, UUID.randomUUID(), "en"))
                .isInstanceOf(ApiException.class)
                .hasMessageContaining("No such offer");
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
