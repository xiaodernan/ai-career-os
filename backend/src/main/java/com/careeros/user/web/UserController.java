package com.careeros.user.web;

import com.careeros.auth.dto.MeResponse;
import com.careeros.auth.dto.UpdateMeRequest;
import com.careeros.auth.service.UserService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.user.dto.ProfileResponse;
import com.careeros.user.dto.UpdateProfileRequest;
import com.careeros.user.service.UserProfileService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Frontend-facing alias of the /me surface: /api/v1/users/me + /api/v1/users/me/profile. */
@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserService userService;
    private final UserProfileService profileService;

    public UserController(UserService userService, UserProfileService profileService) {
        this.userService = userService;
        this.profileService = profileService;
    }

    @GetMapping("/me")
    public MeResponse me(@CurrentUser AuthUser user) {
        return userService.get(user.id());
    }

    @PatchMapping("/me")
    public MeResponse updateMe(@CurrentUser AuthUser user, @RequestBody @Valid UpdateMeRequest request) {
        return userService.update(user.id(), request);
    }

    @GetMapping("/me/profile")
    public ProfileResponse profile(@CurrentUser AuthUser user) {
        return profileService.get(user.id());
    }

    @PatchMapping("/me/profile")
    public ProfileResponse updateProfile(@CurrentUser AuthUser user,
                                         @RequestBody @Valid UpdateProfileRequest request) {
        return profileService.update(user.id(), request);
    }
}
