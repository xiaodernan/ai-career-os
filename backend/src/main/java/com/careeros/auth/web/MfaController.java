package com.careeros.auth.web;

import com.careeros.auth.dto.MfaActivateRequest;
import com.careeros.auth.dto.MfaEnrollResponse;
import com.careeros.auth.dto.MfaProofRequest;
import com.careeros.auth.dto.MfaRecoveryCodesResponse;
import com.careeros.auth.dto.MfaStatusResponse;
import com.careeros.auth.service.MfaService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The second door's management surface (roadmaps 36.1 and 36.3). Every route sits behind the
 * signed-in session: enrolling under someone else's account is not a thing a code can prove.
 *
 * <p>{@code POST /enroll} is the only route that answers a seed. It answers a fresh one every
 * call while the enrollment is unproven, so a screen that lost the QR code can ask again; an
 * enabled second factor refuses (409) rather than minting a second seed. {@code POST /activate}
 * is the proof: it answers the ten recovery codes exactly once and never again.
 * {@code POST /recovery-codes} reprints that set and revokes the old one, and
 * {@code POST /disable} takes the door off -- both after the password and a working code, and
 * both POSTs rather than a DELETE on {@code /me/mfa}, because the limiter meters a route's
 * whole URI: a DELETE beside the status GET would put the settings card's own reads in the
 * same five-a-minute bucket as the code guesses.
 */
@RestController
@RequestMapping("/api/v1/me/mfa")
public class MfaController {

    private final MfaService mfa;

    public MfaController(MfaService mfa) {
        this.mfa = mfa;
    }

    @GetMapping
    public MfaStatusResponse status(@CurrentUser AuthUser user) {
        MfaService.Status status = mfa.status(user.id());
        return new MfaStatusResponse(status.enabled(), status.pending(),
                status.recoveryCodesRemaining());
    }

    @PostMapping("/enroll")
    public MfaEnrollResponse enroll(@CurrentUser AuthUser user) {
        MfaService.Enrollment enrollment = mfa.enroll(user.id());
        return new MfaEnrollResponse(enrollment.secret(), enrollment.otpauthUri());
    }

    @PostMapping("/activate")
    public MfaRecoveryCodesResponse activate(@CurrentUser AuthUser user,
                                             @RequestBody @Valid MfaActivateRequest request) {
        return new MfaRecoveryCodesResponse(
                mfa.activate(user.id(), request.password(), request.code()).recoveryCodes());
    }

    @PostMapping("/recovery-codes")
    public MfaRecoveryCodesResponse reissueRecoveryCodes(@CurrentUser AuthUser user,
                                                         @RequestBody @Valid MfaProofRequest request) {
        return new MfaRecoveryCodesResponse(
                mfa.reissueRecoveryCodes(user.id(), request.password(), request.code())
                        .recoveryCodes());
    }

    @PostMapping("/disable")
    public Map<String, Object> disable(@CurrentUser AuthUser user,
                                       @RequestBody @Valid MfaProofRequest request) {
        mfa.disable(user.id(), request.password(), request.code());
        return Map.of("disabled", true);
    }
}
