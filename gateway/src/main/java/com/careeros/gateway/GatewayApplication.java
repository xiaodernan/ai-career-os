package com.careeros.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * The edge of the system (Epic 88).
 *
 * <p>The browser talks to one address; the gateway decides which service answers. Today
 * that is the domain backend, with the engine still reached through it -- the backend owns
 * the internal token and the circuit around the engine, and nothing at the edge should
 * know those secrets. Keeping one front door means CORS, request ids and, later, rate
 * limits are configured once rather than in every caller.
 */
@SpringBootApplication
public class GatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
