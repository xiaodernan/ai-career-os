package com.careeros.discovery;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.netflix.eureka.server.EnableEurekaServer;

/**
 * The registry every other process can point at (Epic 98).
 *
 * <p>The stack's upstreams are already addressed through Spring Cloud's discovery
 * abstraction: the gateway asks the load balancer for `backend` rather than for a URL.
 * The simple client made that abstraction true with a configuration list; this process
 * makes it true with a registry, so a second backend instance becomes a fact the
 * registry knows rather than an entry every edge must be redeployed to learn.
 *
 * <p>It is deliberately a separate application rather than a library: a registry that
 * shares a JVM with the service it describes cannot report that service's death, and a
 * rolling deploy of the service would restart the answer.
 */
@SpringBootApplication
@EnableEurekaServer
public class DiscoveryApplication {

    public static void main(String[] args) {
        SpringApplication.run(DiscoveryApplication.class, args);
    }
}
