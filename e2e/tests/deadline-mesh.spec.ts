import { expect, test } from "./fixtures";
import { API_URL } from "./fixtures";

/**
 * The deadline mesh (Epic 128) -- the caller's own budget, enforced at the backend
 * before any engine token is spent.
 *
 * `X-Request-Deadline-Ms` carries an epoch millisecond. A caller that has stopped
 * waiting (fetch aborted at 1 ms, a queue timeout, a page that moved on) is refused
 * with 502 AI_SERVICE_UNAVAILABLE *before* the backend asks the engine to work, which
 * is the one cheap check the mesh owes the token buyer. A future value is kept, an
 * absent value is treated as no budget, and a malformed value is ignored -- never a
 * refusal, because a malformed deadline is not a reason to lose a customer.
 *
 * Four calls, four honest answers, through the real stack:
 *   past deadline   -> 502 AI_SERVICE_UNAVAILABLE (engine never asked; returns in <1.5s)
 *   future deadline -> 200 (the mesh keeps the caller's budget)
 *   absent          -> 200 (no budget stated)
 *   malformed       -> 200 (malformed is not a refusal)
 */
test("the deadline mesh refuses the caller whose budget passed, before the engine is asked", async ({
  request,
  user,
}) => {
  const headers = { Authorization: `Bearer ${user.accessToken}` };

  // Past deadline: epoch 1ms. The mesh must refuse fast -- the engine must never be asked.
  const t0 = Date.now();
  const past = await request.post(`${API_URL}/copilot/chat`, {
    headers: { ...headers, "X-Request-Deadline-Ms": "1" },
    data: { message: "hi" },
  });
  const elapsed = Date.now() - t0;
  expect(past.status()).toBe(502);
  expect(elapsed).toBeLessThan(1500);
  const pastBody = (await past.json()) as {
    success: boolean;
    error?: { code?: string; message?: string };
  };
  expect(pastBody.success).toBe(false);
  expect(pastBody.error?.code).toBe("AI_SERVICE_UNAVAILABLE");

  // Future deadline: the mesh keeps the caller's budget.
  const future = String(Date.now() + 30_000);
  const kept = await request.post(`${API_URL}/copilot/chat`, {
    headers: { ...headers, "X-Request-Deadline-Ms": future },
    data: { message: "Say only OK" },
  });
  expect(kept.status()).toBe(200);

  // No header at all: behaves as before the header existed.
  const absent = await request.post(`${API_URL}/copilot/chat`, {
    headers,
    data: { message: "Say only OK" },
  });
  expect(absent.status()).toBe(200);

  // A malformed deadline is ignored, never a refusal.
  const malformed = await request.post(`${API_URL}/copilot/chat`, {
    headers: { ...headers, "X-Request-Deadline-Ms": "banana" },
    data: { message: "Say only OK" },
  });
  expect(malformed.status()).toBe(200);
});
