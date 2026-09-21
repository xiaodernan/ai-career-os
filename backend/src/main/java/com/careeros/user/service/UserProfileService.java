package com.careeros.user.service;

import com.careeros.auth.entity.User;
import com.careeros.auth.entity.UserProfile;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.user.dto.ProfileResponse;
import com.careeros.user.dto.UpdateProfileRequest;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** /api/v1/users/me* surface; every access is scoped to the authenticated user id. */
@Service
public class UserProfileService {

    private final UserRepository users;
    private final UserProfileRepository profiles;

    public UserProfileService(UserRepository users, UserProfileRepository profiles) {
        this.users = users;
        this.profiles = profiles;
    }

    @Transactional(readOnly = true)
    public ProfileResponse get(UUID userId) {
        return ProfileResponse.from(requireProfile(userId));
    }

    @Transactional
    public ProfileResponse update(UUID userId, UpdateProfileRequest request) {
        User user = users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.NOT_FOUND, "User not found"));
        UserProfile profile = requireProfile(userId);
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
        profiles.save(profile);
        users.save(user);
        return ProfileResponse.from(profile);
    }

    private UserProfile requireProfile(UUID userId) {
        return profiles.findByUserId(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.NOT_FOUND, "Profile not found"));
    }
}
