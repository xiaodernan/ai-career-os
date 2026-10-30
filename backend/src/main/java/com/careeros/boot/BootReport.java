package com.careeros.boot;

import com.careeros.auth.service.ConsoleEmailSender;
import com.careeros.auth.service.EmailSender;
import com.careeros.auth.service.SmtpEmailSender;
import com.careeros.config.AppProperties;
import com.careeros.push.service.NoopPushSender;
import com.careeros.push.service.PushSender;
import com.careeros.storage.StorageService;
import java.lang.reflect.Method;
import java.net.URI;
import java.util.TreeSet;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.data.redis.RedisProperties;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.boot.web.context.WebServerApplicationContext;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationListener;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The one line a started backend says about what it became (roadmap 39.3).
 *
 * <p>A stack can look healthy and still be the wrong one: a dev mail transport in a
 * production compose, a database that belongs to the previous deployment, push silently
 * off. Every fact here comes from the object the process is actually using -- the bound
 * properties, the chosen mail and push beans, the store bean's presence, and the
 * scheduler registrations the context really owns -- so the sentence cannot disagree
 * with the behaviour it describes.
 *
 * <p>Only hosts, names and choices are printed. URLs are parsed for their host, never
 * echoed (a JDBC or Redis URL can carry credentials), no secret is read at all, and the
 * VAPID pair is reported as on or off rather than quoted. {@code BootReportTest} builds
 * the report from values whose every secret is a sentinel and asserts none of them
 * appears in the line.
 */
@Component
public class BootReport implements ApplicationListener<ApplicationReadyEvent> {

    private static final Logger log = LoggerFactory.getLogger(BootReport.class);

    private final AppProperties props;
    private final DataSourceProperties dataSource;
    private final RedisProperties redis;
    private final EmailSender email;
    private final PushSender push;
    private final ObjectProvider<StorageService> storage;
    private final ApplicationContext context;

    public BootReport(AppProperties props, DataSourceProperties dataSource, RedisProperties redis,
            EmailSender email, PushSender push, ObjectProvider<StorageService> storage,
            ApplicationContext context) {
        this.props = props;
        this.dataSource = dataSource;
        this.redis = redis;
        this.email = email;
        this.push = push;
        this.storage = storage;
        this.context = context;
    }

    @Override
    public void onApplicationEvent(ApplicationReadyEvent event) {
        int port = 0;
        if (event.getApplicationContext() instanceof WebServerApplicationContext web
                && web.getWebServer() != null) {
            port = web.getWebServer().getPort();
        }
        log.info("boot: {}", line(port));
    }

    /** The line itself, split out of the listener so a test can read it without a context. */
    String line(int port) {
        StringBuilder line = new StringBuilder()
                .append("env=").append(props.getDeployment().getEnv())
                .append(" port=").append(port)
                .append(" db=").append(database())
                .append(" redis=").append(redisHost())
                .append(' ');
        if (storage.getIfAvailable() == null) {
            line.append("storage=off");
        } else {
            String bucket = props.getStorage().getBucket();
            line.append("storage=").append(host(props.getStorage().getEndpoint()))
                    .append(" bucket=").append(bucket == null || bucket.isBlank() ? "unset" : bucket.trim());
        }
        return line
                .append(" ai=").append(host(props.getAiService().getBaseUrl()))
                .append(" mail=").append(mail())
                .append(" push=").append(push instanceof NoopPushSender ? "off" : "keypair")
                .append(" schedulers=").append(schedulers())
                .toString();
    }

    private String database() {
        URI uri = uri(dataSource.getUrl(), true);
        if (uri == null) {
            String url = dataSource.getUrl();
            return url == null || url.isBlank() ? "unset" : "unparseable";
        }
        String host = uri.getHost();
        if (host == null) {
            return "unparseable";
        }
        String path = uri.getPath();
        return path == null || path.isBlank() || "/".equals(path) ? host : host + path;
    }

    private String redisHost() {
        String url = redis.getUrl();
        if (url != null && !url.isBlank()) {
            return host(url);
        }
        String host = redis.getHost();
        return host == null || host.isBlank() ? "unset" : host.trim();
    }

    private String mail() {
        if (email instanceof ConsoleEmailSender) {
            return "console";
        }
        if (email instanceof SmtpEmailSender) {
            return "smtp";
        }
        return email.getClass().getSimpleName();
    }

    /** The beans the context holds that declare a {@code @Scheduled} method: spring's clock is on. */
    private String schedulers() {
        TreeSet<String> names = new TreeSet<>();
        for (String name : context.getBeanDefinitionNames()) {
            Class<?> type = context.getType(name);
            if (type != null && scheduled(type)) {
                names.add(type.getSimpleName());
            }
        }
        return names.toString();
    }

    private static boolean scheduled(Class<?> type) {
        for (Method method : type.getDeclaredMethods()) {
            if (method.isAnnotationPresent(Scheduled.class)) {
                return true;
            }
        }
        return false;
    }

    private static String host(String url) {
        URI uri = uri(url, false);
        if (uri == null) {
            return url == null || url.isBlank() ? "unset" : "unparseable";
        }
        String host = uri.getHost();
        return host == null ? "unparseable" : host;
    }

    /** A URL's shape without its credentials: the host is all the line is allowed to keep. */
    private static URI uri(String value, boolean jdbc) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String raw = value.trim();
        if (jdbc && raw.regionMatches(true, 0, "jdbc:", 0, 5)) {
            raw = raw.substring(5);
        }
        try {
            return URI.create(raw);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
