package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.auth.dto.UpdateMeRequest;
import com.careeros.auth.entity.User;
import com.careeros.auth.entity.UserProfile;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.auth.repository.UserRepository;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Epic 414 — the profile door takes the same cleaned name as registration, so a
 * control character cannot be written a day after the account was created.
 */
class UserServiceDisplayNameTest {

    @Test
    void aProfileUpdateStoresTheCleanedName() {
        UUID id = UUID.randomUUID();
        User user = new User();
        user.setId(id);
        user.setEmail("ada@example.invalid");
        user.setDisplayName("Ada");
        user.setRole("USER");
        user.setLocale("en");
        UserProfile profile = new UserProfile();
        profile.setUserId(id);

        UserRepository users = mock(UserRepository.class);
        UserProfileRepository profiles = mock(UserProfileRepository.class);
        when(users.findById(id)).thenReturn(Optional.of(user));
        when(profiles.findByUserId(id)).thenReturn(Optional.of(profile));

        new UserService(users, profiles).update(id,
                new UpdateMeRequest("  Ada\u0007\n  Lovelace  ", null, null, null, null,
                        null, null, null, null, null, null));

        assertThat(user.getDisplayName()).isEqualTo("Ada Lovelace");
    }
}
