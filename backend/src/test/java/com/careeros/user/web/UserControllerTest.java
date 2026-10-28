package com.careeros.user.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.entity.User;
import com.careeros.auth.entity.UserProfile;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.auth.service.AccountErasureService;
import com.careeros.auth.service.AuthService;
import com.careeros.auth.service.UserService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.user.service.UserProfileService;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The /api/v1/users/me* surface — the frontend's profile editor — had no test knocking on
 * it: grep for "users/me" under backend/src/test returned only the auth-flow IT hitting the
 * OTHER controller (/api/v1/me, MeController), while this alias's routes and the two services
 * behind them (UserService.update, UserProfileService.update) were never stated anywhere.
 *
 * Both services implement the same contract — "all fields optional; null means leave
 * unchanged" — nine times over, by hand, field by field. That repetition is exactly where a
 * missing null-check or a stray overwrite hides, so the two PATCH tests below pin it: one
 * changes a single field and asserts every other field kept its value, twice, once per
 * surface.
 *
 * The services run for real here (mocked repositories only): the null-means-unchanged logic,
 * the trim calls, the missing-profile 404 and the principal-scoped lookups are all under
 * test. The advice, handler and argument resolver are the production three, so validation
 * failures and unauthenticated requests travel the same paths they travel in the running app.
 */
class UserControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");

    private UserRepository users;
    private UserProfileRepository profiles;
    private AuthService authService;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        profiles = mock(UserProfileRepository.class);
        authService = mock(AuthService.class);
        UserService userService = new UserService(users, profiles);
        UserProfileService profileService = new UserProfileService(users, profiles);
        mvc = MockMvcBuilders.standaloneSetup(new UserController(userService, profileService, authService,
                        mock(AccountErasureService.class), mock(com.careeros.auth.service.TokenService.class)))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        as(ALICE);
        givenUserAndProfile();
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    private static void as(UUID id) {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(id, "ada@example.invalid", "user"), null, List.of()));
    }

    private void givenUserAndProfile() {
        User user = new User();
        user.setId(ALICE);
        user.setEmail("ada@example.invalid");
        user.setDisplayName("Ada Lovelace");
        when(users.findById(ALICE)).thenReturn(Optional.of(user));

        UserProfile profile = new UserProfile();
        profile.setUserId(ALICE);
        profile.setHeadline("Backend engineer");
        profile.setSummary("Builds distributed systems.");
        profile.setLocation("London");
        profile.setYearsExperience(new BigDecimal("7.5"));
        profile.setTargetRoles(List.of("Backend Engineer", "Platform Engineer"));
        profile.setTargetLocations(List.of("London", "Remote"));
        Map<String, Object> links = new HashMap<>();
        links.put("github", "https://github.com/ada");
        profile.setLinks(links);
        profile.setWorkAuthorization(Map.of("status", "citizen"));
        profile.setPreferences(Map.of("theme", "dark"));
        when(profiles.findByUserId(ALICE)).thenReturn(Optional.of(profile));
    }

    // ------------------------------------------------------------ GET: the shape both surfaces answer with

    @Test
    void the_me_alias_answers_the_display_name_and_profile_fields_in_the_envelope() throws Exception {
        mvc.perform(get("/api/v1/users/me"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.displayName").value("Ada Lovelace"))
                .andExpect(jsonPath("$.data.email").value("ada@example.invalid"))
                .andExpect(jsonPath("$.data.locale").value("en"))
                .andExpect(jsonPath("$.data.headline").value("Backend engineer"))
                .andExpect(jsonPath("$.data.location").value("London"))
                .andExpect(jsonPath("$.data.yearsExperience").value(7.5))
                .andExpect(jsonPath("$.data.targetRoles[0]").value("Backend Engineer"))
                .andExpect(jsonPath("$.data.preferences.theme").value("dark"));
    }

    @Test
    void the_profile_alias_answers_the_full_row_the_editor_needs() throws Exception {
        mvc.perform(get("/api/v1/users/me/profile"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.userId").value(ALICE.toString()))
                .andExpect(jsonPath("$.data.summary").value("Builds distributed systems."))
                .andExpect(jsonPath("$.data.links.github").value("https://github.com/ada"))
                .andExpect(jsonPath("$.data.workAuthorization.status").value("citizen"));
    }

    // ------------------------------------------------------------ PATCH: null means unchanged, on both surfaces

    @Test
    void one_field_in_a_me_patch_leaves_every_other_field_untouched() throws Exception {
        // The contract, stated once: "all fields optional; null means leave unchanged".
        // Nine fields, nine null-checks — a missed one would wipe the field on every
        // save from the settings page. Only displayName is sent here.
        mvc.perform(patch("/api/v1/users/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"displayName\":\"  Ada King  \"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.displayName").value("Ada King"))
                .andExpect(jsonPath("$.data.headline").value("Backend engineer"))
                .andExpect(jsonPath("$.data.location").value("London"))
                .andExpect(jsonPath("$.data.yearsExperience").value(7.5))
                .andExpect(jsonPath("$.data.targetRoles[0]").value("Backend Engineer"))
                .andExpect(jsonPath("$.data.links.github").value("https://github.com/ada"))
                .andExpect(jsonPath("$.data.preferences.theme").value("dark"));

        ArgumentCaptor<User> saved = ArgumentCaptor.forClass(User.class);
        verify(users).save(saved.capture());
        assertThat(saved.getValue().getDisplayName()).isEqualTo("Ada King");
        // The service saves the profile row unconditionally (a no-op when nothing named a
        // profile field) — what matters is that every profile field on it kept its value.
        ArgumentCaptor<UserProfile> profileSaved = ArgumentCaptor.forClass(UserProfile.class);
        verify(profiles).save(profileSaved.capture());
        UserProfile kept = profileSaved.getValue();
        assertThat(kept.getHeadline()).isEqualTo("Backend engineer");
        assertThat(kept.getSummary()).isEqualTo("Builds distributed systems.");
        assertThat(kept.getTargetRoles()).containsExactly("Backend Engineer", "Platform Engineer");
        assertThat(kept.getLinks()).containsEntry("github", "https://github.com/ada");
    }

    @Test
    void one_field_in_a_profile_patch_leaves_every_other_profile_field_untouched() throws Exception {
        // Same contract on the other alias. The settings page patches headline and expects
        // summary, roles, links and preferences to survive the round trip.
        mvc.perform(patch("/api/v1/users/me/profile")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"headline\":\"Staff backend engineer\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.headline").value("Staff backend engineer"))
                .andExpect(jsonPath("$.data.summary").value("Builds distributed systems."))
                .andExpect(jsonPath("$.data.location").value("London"))
                .andExpect(jsonPath("$.data.yearsExperience").value(7.5))
                .andExpect(jsonPath("$.data.targetRoles[1]").value("Platform Engineer"))
                .andExpect(jsonPath("$.data.targetLocations[0]").value("London"))
                .andExpect(jsonPath("$.data.links.github").value("https://github.com/ada"))
                .andExpect(jsonPath("$.data.workAuthorization.status").value("citizen"))
                .andExpect(jsonPath("$.data.preferences.theme").value("dark"));

        ArgumentCaptor<UserProfile> saved = ArgumentCaptor.forClass(UserProfile.class);
        verify(profiles).save(saved.capture());
        assertThat(saved.getValue().getHeadline()).isEqualTo("Staff backend engineer");
    }

    @Test
    void a_blank_display_name_is_refused_before_the_service_sees_it() throws Exception {
        // @Size(min = 1): an empty name is a validation failure with a field-level detail,
        // not a silent wipe of the name the header renders.
        mvc.perform(patch("/api/v1/users/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"displayName\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("displayName"));

        verify(users, never()).save(any());
    }

    @Test
    void a_locale_switch_writes_the_account_and_the_answer_reads_it_back() throws Exception {
        mvc.perform(patch("/api/v1/users/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"locale\":\"zh\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.locale").value("zh"))
                .andExpect(jsonPath("$.data.displayName").value("Ada Lovelace"));

        ArgumentCaptor<User> saved = ArgumentCaptor.forClass(User.class);
        verify(users).save(saved.capture());
        assertThat(saved.getValue().getLocale()).isEqualTo("zh");
        // The same row answers the next read: the account keeps the language, it is not a
        // per-request decoration.
        mvc.perform(get("/api/v1/users/me"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.locale").value("zh"));
    }

    @Test
    void a_language_the_product_does_not_speak_is_refused_before_the_service_sees_it() throws Exception {
        mvc.perform(patch("/api/v1/users/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"locale\":\"fr\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("locale"));

        verify(users, never()).save(any());
    }

    @Test
    void an_out_of_range_experience_is_refused_on_both_surfaces() throws Exception {
        mvc.perform(patch("/api/v1/users/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"yearsExperience\":61}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.details[0].field").value("yearsExperience"))
                // The default Jakarta message for @DecimalMax, which is what ships.
                .andExpect(jsonPath("$.error.details[0].message")
                        .value("must be less than or equal to 60"));

        mvc.perform(patch("/api/v1/users/me/profile")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"yearsExperience\":-1}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.details[0].field").value("yearsExperience"));

        verifyNoInteractions(users, profiles);
    }

    // ------------------------------------------------------------ who is asking, and what is missing

    @Test
    void an_unauthenticated_caller_is_refused_before_the_service_runs() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/users/me")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        mvc.perform(get("/api/v1/users/me/profile")).andExpect(status().isUnauthorized());
        mvc.perform(patch("/api/v1/users/me/profile")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}")).andExpect(status().isUnauthorized());

        verifyNoInteractions(users, profiles);
    }

    @Test
    void the_id_the_repositories_are_asked_with_is_the_principals_and_never_a_request_field()
            throws Exception {
        // IDOR-proofness, stated where it can be verified: both services take the id from
        // the @CurrentUser parameter, which the resolver reads from the SecurityContext.
        // No field of the request body can reach the repository — the request has no place
        // to put one, and this test proves the lookup is the principal's id either way.
        mvc.perform(get("/api/v1/users/me")).andExpect(status().isOk());

        ArgumentCaptor<UUID> userLooked = ArgumentCaptor.forClass(UUID.class);
        verify(users).findById(userLooked.capture());
        ArgumentCaptor<UUID> profileLooked = ArgumentCaptor.forClass(UUID.class);
        verify(profiles).findByUserId(profileLooked.capture());

        assertThat(userLooked.getValue()).isEqualTo(ALICE);
        assertThat(profileLooked.getValue()).isEqualTo(ALICE);
    }

    @Test
    void a_user_without_a_profile_row_is_a_404_not_a_500() throws Exception {
        // Registration creates user + profile in one flow, but a half-created row (or a
        // manual DB edit) would otherwise surface as NullPointerException in from().
        when(profiles.findByUserId(ALICE)).thenReturn(Optional.empty());

        mvc.perform(get("/api/v1/users/me/profile"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("PROFILE_NOT_FOUND"))
                .andExpect(jsonPath("$.error.message").value("Profile not found"));

        mvc.perform(get("/api/v1/users/me"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.message").value("Profile not found"));
    }

    @Test
    void an_unknown_principal_is_a_404_before_the_profile_is_consulted() throws Exception {
        when(users.findById(any())).thenReturn(Optional.empty());

        mvc.perform(patch("/api/v1/users/me")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"displayName\":\"X\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.message").value("User not found"));
    }
}
