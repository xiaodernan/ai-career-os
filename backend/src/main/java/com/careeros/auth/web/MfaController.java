package com.careeros.auth.web;

import com.careeros.auth.dto.MfaActivateRequest;
import com.careeros.auth.dto.MfaActivateResponse;
import com.careeros.auth.dto.MfaEnrollResponse;
import com.careeros.auth.dto.MfaStatusResponse;
import com.careeros.auth.service.MfaService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The second door's enrollment surface (roadmap 36.1). All three routes sit behind the signed-in
 * session: enrolling under someone else's account is not a thing a code can prove.
 *
 * <p>{@code POST /enroll} is the only route that answers a seed. It answers a fresh one every
 * call while the enrollment is unproven, so a screen that lost the QR code can ask again; an
 * enabled second factor refuses (409) rather than minting a second seed. {@code POST /activate}
 * is the proof: it answers the ten recovery codes exactly once and never again.
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
        return new MfaStatusResponse(status.enabled(), status.pending());
    }

    @PostMapping("/enroll")
    public MfaEnrollResponse enroll(@CurrentUser AuthUser user) {
        MfaService.Enrollment enrollment = mfa.enroll(user.id());
        return new MfaEnrollResponse(enrollment.secret(), enrollment.otpauthUri());
    }

    @PostMapping("/activate")
    public MfaActivateResponse activate(@CurrentUser AuthUser user,
                                        @RequestBody @Valid MfaActivateRequest request) {
        return new MfaActivateResponse(
                mfa.activate(user.id(), request.password(), request.code()).recoveryCodes());
    }
}
