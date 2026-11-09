package com.careeros.system;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The fleet an operator can see, behind the same authentication as the rest of the API
 * (Epic 100). It is deliberately not part of `/health`: that route is public, and the
 * internal addresses of the fleet are not.
 */
@RestController
@RequestMapping("/api/v1/system")
public class ServiceTopologyController {

    private final ServiceTopologyService topology;

    public ServiceTopologyController(ServiceTopologyService topology) {
        this.topology = topology;
    }

    @GetMapping("/topology")
    public Map<String, Object> topology() {
        return topology.report();
    }
}
