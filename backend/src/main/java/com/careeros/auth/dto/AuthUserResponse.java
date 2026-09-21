package com.careeros.auth.dto;

import com.careeros.auth.entity.User;
import java.util.UUID;

public record AuthUserResponse(UUID id, String email, String displayName, String role) {

    public static AuthUserResponse from(User user) {
        return new AuthUserResponse(user.getId(), user.getEmail(), user.getDisplayName(), user.getRole());
    }
}
