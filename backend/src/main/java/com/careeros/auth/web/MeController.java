package com.careeros.auth.web;

import com.careeros.auth.dto.EraseAccountRequest;
import com.careeros.auth.dto.MeResponse;
import com.careeros.auth.dto.PasswordChangeRequest;
import com.careeros.auth.dto.UpdateMeRequest;
import com.careeros.auth.service.AccountErasureService;
import com.careeros.auth.service.AuthService;
import com.careeros.auth.service.UserService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/me")
public class MeController {

    private final UserService userService;
    private final AuthService authService;
    private final AccountErasureService erasure;

    public MeController(UserService userService, AuthService authService,
                        AccountErasureService erasure) {
        this.userService = userService;
        this.authService = authService;
        this.erasure = erasure;
    }

    @GetMapping
    public MeResponse me(@CurrentUser AuthUser user) {
        return userService.get(user.id());
    }

    @PatchMapping
    public MeResponse update(@CurrentUser AuthUser user, @RequestBody @Valid UpdateMeRequest request) {
        return userService.update(user.id(), request);
    }

    @PatchMapping("/password")
    public Map<String, Object> changePassword(@CurrentUser AuthUser user,
                                              @RequestBody @Valid PasswordChangeRequest request) {
        authService.changePassword(user.id(), request);
        return Map.of("changed", true);
    }

    @PostMapping("/erase")
    public Map<String, Object> erase(@CurrentUser AuthUser user,
                                     @RequestBody @Valid EraseAccountRequest request) {
        erasure.erase(user.id(), request);
        return Map.of("erased", true);
    }
}
