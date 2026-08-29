import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// client.ts keeps module-level token/refresh-promise state, so every test
// needs a fresh module instance — hence the dynamic import after resetModules
// rather than a static import at the top of the file.

function makeJwt(exp: number): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify({ exp }));
  return `${header}.${body}.sig`;
}

describe("api client — refresh race handling", () => {
  let defaultAdapter: MockAdapter;

  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
    defaultAdapter = new MockAdapter(axios);
  });

  afterEach(() => {
    defaultAdapter.restore();
  });

  it("dedupes five concurrent 401s into a single refresh call and retries every request", async () => {
    const { api, setTokens, setOnAuthFailure } = await import("./client");
    const apiAdapter = new MockAdapter(api);

    const expiredAccess = makeJwt(Math.floor(Date.now() / 1000) - 10);
    const freshAccess = makeJwt(Math.floor(Date.now() / 1000) + 900);
    setTokens({ access: expiredAccess, refresh: "refresh-token-1" });

    let refreshCalls = 0;
    defaultAdapter.onPost(/\/auth\/refresh\/$/).reply(() => {
      refreshCalls += 1;
      return [200, { access: freshAccess, refresh: "refresh-token-2" }];
    });

    let signOuts = 0;
    setOnAuthFailure(() => {
      signOuts += 1;
    });

    apiAdapter.onGet("/thing").reply((config) => {
      return config.headers?.Authorization === `Bearer ${freshAccess}` ? [200, { ok: true }] : [401, {}];
    });

    const results = await Promise.all(Array.from({ length: 5 }, () => api.get("/thing")));

    expect(results).toHaveLength(5);
    for (const result of results) {
      expect(result.status).toBe(200);
    }
    expect(refreshCalls).toBe(1);
    expect(signOuts).toBe(0);

    apiAdapter.restore();
    setTokens(null); // cancels the proactive-refresh timer setTokens() scheduled above
  });

  it("signs out exactly once, not once per queued request, when the refresh itself fails", async () => {
    const { api, setTokens, setOnAuthFailure } = await import("./client");
    const apiAdapter = new MockAdapter(api);

    const expiredAccess = makeJwt(Math.floor(Date.now() / 1000) - 10);
    setTokens({ access: expiredAccess, refresh: "refresh-token-1" });

    defaultAdapter.onPost(/\/auth\/refresh\/$/).reply(401, { detail: "Token is blacklisted" });
    apiAdapter.onGet("/thing").reply(401, {});

    let signOuts = 0;
    setOnAuthFailure(() => {
      signOuts += 1;
    });

    const outcomes = await Promise.allSettled(Array.from({ length: 5 }, () => api.get("/thing")));

    expect(outcomes.every((o) => o.status === "rejected")).toBe(true);
    expect(signOuts).toBe(1);

    apiAdapter.restore();
  });
});
