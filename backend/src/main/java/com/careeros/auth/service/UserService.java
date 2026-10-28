package com.careeros.auth.service;

import com.careeros.auth.dto.MeResponse;
import com.careeros.auth.dto.UpdateMeRequest;
import com.careeros.auth.entity.User;
import com.careeros.auth.entity.UserProfile;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Owns the /api/v1/me surface; every access is scoped to the authenticated user id (IDOR-proof). */
@Service
public class UserService {

    private final UserRepository users;
    private final UserProfileRepository profiles;

    public UserService(UserRepository users, UserProfileRepository profiles) {
        this.users = users;
        this.profiles = profiles;
    }

    @Transactional(readOnly = true)
    public MeResponse get(UUID userId) {
        User user = requireUser(userId);
        return MeResponse.of(user.getDisplayName(), user.getEmail(), user.getLocale(),
                requireProfile(userId));
    }

    @Transactional
    public MeResponse update(UUID userId, UpdateMeRequest request) {
        User user = requireUser(userId);
        UserProfile profile = requireProfile(userId);
        if (request.displayName() != null) {
            user.setDisplayName(request.displayName().trim());
        }
        if (request.headline() != null) {
            profile.setHeadline(request.headline().trim());
        }
        if (request.summary() != null) {
            profile.setSummary(request.summary());
        }
        if (request.location() != null) {
            profile.setLocation(request.location().trim());
        }
        if (request.yearsExperience() != null) {
            profile.setYearsExperience(request.yearsExperience());
        }
        if (request.targetRoles() != null) {
            profile.setTargetRoles(request.targetRoles());
        }
        if (request.targetLocations() != null) {
            profile.setTargetLocations(request.targetLocations());
        }
        if (request.links() != null) {
            profile.setLinks(request.links());
        }
        if (request.workAuthorization() != null) {
            profile.setWorkAuthorization(request.workAuthorization());
        }
        if (request.preferences() != null) {
            profile.setPreferences(request.preferences());
        }
        if (request.locale() != null) {
            user.setLocale(request.locale());
        }
        users.save(user);
        profiles.save(profile);
        return MeResponse.of(user.getDisplayName(), user.getEmail(), user.getLocale(), profile);
    }

    private User requireUser(UUID userId) {
        return users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.USER_NOT_FOUND, "User not found"));
    }

    private UserProfile requireProfile(UUID userId) {
        return profiles.findByUserId(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.PROFILE_NOT_FOUND, "Profile not found"));
    }
}
