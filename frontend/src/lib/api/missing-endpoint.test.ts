import { describe, expect, it } from "vitest";

import { missingEndpointMessage } from "./missing-endpoint";

describe("missingEndpointMessage", () => {
  it("names the route that answered 404, so a screenshot is diagnosable", () => {
    expect(missingEndpointMessage("GET /reports/dashboard")).toContain(
      "GET /reports/dashboard answered 404",
    );
  });

  it("says what a 404 means here rather than what the product lacks", () => {
    expect(missingEndpointMessage()).toContain("A route this screen needs answered 404");
  });

  it("never claims the endpoint does not exist, which was false at every call site", () => {
    // The sentences this replaced said the endpoint "isn't live on the backend yet" or
    // "isn't served" -- all of those routes are served, so the copy described the product
    // wrongly and gave the user nothing to act on. Spelling that out here keeps the older
    // wording from creeping back one call site at a time.
    for (const phrase of ["isn't live", "isn\'t served", "isn\'t connected", "isn\'t wired", "yet"]) {
      expect(missingEndpointMessage("GET /jobs")).not.toContain(phrase);
    }
  });
});
