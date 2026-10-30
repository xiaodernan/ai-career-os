package com.careeros.boot;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.auth.service.ConsoleEmailSender;
import com.careeros.auth.service.EmailSender;
import com.careeros.auth.service.SmtpEmailSender;
import com.careeros.config.AppProperties;
import com.careeros.push.service.NoopPushSender;
import com.careeros.push.service.PushSender;
import com.careeros.storage.StorageService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.data.redis.RedisProperties;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.scheduling.annotation.Scheduled;

/**
 * What the boot line says, and what it refuses to say (roadmap 39.3).
 *
 * <p>The line is only worth reading if it repeats the choices the process is actually
 * running on -- the bound properties, the mail and push beans the config chose, the store
 * bean's presence and the schedulers the context registered -- and if the sentence cannot
 * carry a credential out of the process. So the fixtures fill every secret-bearing value
 * with one sentinel and the assertions below look for that sentinel everywhere: in the
 * data source, the Redis URL's userinfo, the object store's endpoint and credentials, the
 * JWT and internal-token properties and the VAPID pair.
 */
class BootReportTest {

    private static final String SECRET = "sentinel-2c9f-do-not-print";

    private final AppProperties props = new AppProperties();
    private final DataSourceProperties dataSource = new DataSourceProperties();
    private final RedisProperties redis = new RedisProperties();

    public static class Nightly {
        @Scheduled(fixedDelay = 60_000)
        public void sweep() {
        }

        @Scheduled(cron = "0 20 3 * * *")
        public void retry() {
        }
    }

    public static class Digest {
        @Scheduled(cron = "0 0 8 * * MON")
        public void compose() {
        }
    }

    public static class Plain {
        public void hello() {
        }
    }

    @Test
    void theLineNamesWhatTheProcessBecameAndCarriesNoSecret() throws Exception {
        props.getDeployment().setEnv("prod");
        props.getStorage().setEndpoint("http://" + SECRET + "@objects.internal:9000");
        props.getStorage().setBucket("career_os_files");
        props.getStorage().setAccessKey(SECRET);
        props.getStorage().setSecretKey(SECRET);
        props.getAiService().setBaseUrl("http://" + SECRET + "@ai.internal:8000");
        props.getJwt().setSecret(SECRET);
        props.getInternal().setToken(SECRET);
        dataSource.setUrl("jdbc:postgresql://db.internal:5432/career_os?user=" + SECRET);
        dataSource.setPassword(SECRET);
        redis.setUrl("redis://:" + SECRET + "@cache.internal:6379/0");

        String line = report(mock(StorageService.class), mock(SmtpEmailSender.class),
                mock(PushSender.class), context(Nightly.class, Digest.class, Plain.class)).line(8080);

        assertThat(line).isEqualTo("env=prod port=8080 db=db.internal/career_os "
                + "redis=cache.internal storage=objects.internal bucket=career_os_files "
                + "ai=ai.internal mail=smtp push=keypair schedulers=[Digest, Nightly]");
        assertThat(line).doesNotContain(SECRET);
        assertThat(line).doesNotContain("jdbc:", "postgresql", "redis://", "@");
    }

    @Test
    void storageAndPushThatAreOffSaySoAndAnUnsetDatabaseSaysUnset() {
        EmailSender console = new ConsoleEmailSender(false);

        String line = report(null, console, new NoopPushSender(), context(Plain.class)).line(8080);

        assertThat(line).isEqualTo("env=dev port=8080 db=unset redis=localhost storage=off "
                + "ai=localhost mail=console push=off schedulers=[]");
    }

    @Test
    void aValueTheLineCannotReadIsNamedRatherThanEchoed() {
        props.getStorage().setEndpoint("not a uri " + SECRET);
        props.getAiService().setBaseUrl("also not a uri " + SECRET);
        dataSource.setUrl("jdbc:postgresql://db1,db2,db3/career_os");

        String line = report(mock(StorageService.class), new ConsoleEmailSender(false),
                new NoopPushSender(), context(Plain.class)).line(7000);

        assertThat(line).contains("port=7000")
                .contains("db=unparseable")
                .contains("storage=unparseable bucket=unset")
                .contains("ai=unparseable")
                .doesNotContain(SECRET)
                .doesNotContain("db1,db2,db3");
    }

    private BootReport report(StorageService store, EmailSender email, PushSender push,
            ApplicationContext context) {
        return new BootReport(props, dataSource, redis, email, push,
                provider(store == null ? List.of() : List.of(store)), context);
    }

    @SuppressWarnings("unchecked")
    private static <T> ObjectProvider<T> provider(List<T> beans) {
        ObjectProvider<T> provider = mock(ObjectProvider.class);
        when(provider.getIfAvailable()).thenReturn(beans.isEmpty() ? null : beans.get(0));
        return provider;
    }

    private static ApplicationContext context(Class<?>... beans) {
        AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext();
        context.register(beans);
        context.refresh();
        return context;
    }
}
