package com.careeros.health;

import java.sql.Connection;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/health")
public class HealthController {

    private final DataSource dataSource;
    private final RedisTemplate<String, ?> redisTemplate;

    public HealthController(DataSource dataSource, RedisTemplate<String, ?> redisTemplate) {
        this.dataSource = dataSource;
        this.redisTemplate = redisTemplate;
    }

    @GetMapping
    public Map<String, Object> health() {
        Map<String, Object> body = new LinkedHashMap<>();
        boolean db = dbUp();
        boolean redis = redisUp();
        body.put("status", db && redis ? "ok" : "degraded");
        body.put("db", db);
        body.put("redis", redis);
        return body;
    }

    private boolean dbUp() {
        try (Connection connection = dataSource.getConnection()) {
            return connection.isValid(2);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean redisUp() {
        try {
            redisTemplate.execute(connection -> connection.ping(), true);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
