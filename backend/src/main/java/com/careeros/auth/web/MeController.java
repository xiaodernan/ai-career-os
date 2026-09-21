package com.careeros.auth.web;

import com.careeros.auth.dto.MeResponse;
import com.careeros.auth.dto.UpdateMeRequest;
import com.careeros.auth.service.UserService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/me")
public class MeController {

    private final UserService userService;

    public MeController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public MeResponse me(@CurrentUser AuthUser user) {
        return userService.get(user.id());
    }

    @PatchMapping
    public MeResponse update(@CurrentUser AuthUser user, @RequestBody @Valid UpdateMeRequest request) {
        return userService.update(user.id(), request);
    }
}
