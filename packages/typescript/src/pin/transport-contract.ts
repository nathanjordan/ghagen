/**
 * The one canned `HttpClient` double, plus the transport conformance table.
 *
 * Every adapter behind `HttpClient` — the production `FetchTransport` and the
 * canned `FakeTransport` alike — must satisfy the same table, so a double
 * cannot drift into a shape the real adapter is unable to produce. The Python
 * peer (`tests/test_pin/transport_contract.py`) runs the identical rows.
 *
 * Two builders construct canned responses: `canned()` encodes a JSON value,
 * `cannedRaw()` takes a body verbatim (a malformed 200, a truncated payload).
 *
 * Rows 9-14 put the adapter in front of a **raw socket**, not a
 * request-handling server: `node:http`'s `createServer` always frames a
 * well-formed response, so it cannot express "peer closes without answering"
 * (row 10), "declared `Content-Length: 100`, delivered 5 bytes" (row 12),
 * "trickle a body byte at a time forever" (row 13), or "trickle a *head*
 * byte at a time, forever, never completing it" (row 14).
 *
 * Test-only; excluded from the build in `tsconfig.json` beside
 * `src/integration/test-utils.ts`.
 */

import { expect } from "vitest";
import { createServer, type AddressInfo, type Server, type Socket } from "node:net";
import { HttpResponse, TransportError, type HttpClient, type RequestOptions } from "./github.js";

/** The deadline the adapter under test is built with for the response rows. */
export const RESPONSE_DEADLINE_MS = 5_000;

/** Row 11's deadline, and the sole caller of the adapters' deadline argument. */
export const FAILURE_DEADLINE_MS = 250;

/**
 * Upper bound on a failure row's wall clock, at 10x the deadline. No lower
 * bound is asserted: a "did it really wait?" check flakes on a fast machine and
 * adds nothing the ceiling and the rejected type do not already establish.
 */
export const FAILURE_CEILING_MS = 2_500;

// ---- the one canned double ----

/** Options shared by both canned-response builders. */
export interface CannedOptions {
  status?: number;
  /** Python's `reason`; the name stays TS-idiomatic. */
  statusText?: string;
  headers?: Record<string, string>;
}

/** Build a canned `HttpResponse` whose body is `value` encoded as JSON. */
export function canned(value: unknown, options: CannedOptions = {}): HttpResponse {
  return cannedRaw(JSON.stringify(value), options);
}

/** Build a canned `HttpResponse` around a verbatim body. */
export function cannedRaw(body: string, options: CannedOptions = {}): HttpResponse {
  return new HttpResponse(
    options.status ?? 200,
    body,
    options.statusText ?? "",
    options.headers ?? {},
  );
}

/** What a `FakeTransport` entry may map a URL substring to. */
export type Canned = HttpResponse | HttpResponse[] | Error;

/**
 * Canned `HttpClient` keyed by URL substring.
 *
 * Each entry maps a URL substring to a response, a list of responses (consumed
 * in order, for pagination), or an error to throw. Unmatched URLs return a 404.
 * Requested tokens are recorded on `tokens`, requested URLs on `calls`.
 */
export class FakeTransport implements HttpClient {
  readonly calls: string[] = [];
  readonly tokens: Array<string | undefined> = [];

  constructor(private readonly responses: Record<string, Canned> = {}) {}

  async get(url: string, options: RequestOptions = {}): Promise<HttpResponse> {
    this.calls.push(url);
    this.tokens.push(options.token);
    for (const [pattern, value] of Object.entries(this.responses)) {
      if (url.includes(pattern)) {
        if (Array.isArray(value)) {
          return value.shift()!;
        }
        if (value instanceof Error) {
          throw value;
        }
        return value;
      }
    }
    return new HttpResponse(404, "{}", "Not Found");
  }
}

// ---- the conformance table ----

/**
 * A row that must produce a resolved `HttpResponse` (rows 1-8).
 *
 * One description serves both kinds of adapter: `wire()` is what a raw origin
 * writes to the socket, `response()` is the equivalent canned `HttpResponse`.
 * That is what stops the double from drifting.
 */
export class ResponseCase {
  constructor(
    readonly name: string,
    readonly status: number,
    readonly statusText: string,
    readonly body: string,
    readonly headers: ReadonlyArray<readonly [string, string]> = [],
    readonly token?: string,
  ) {}

  /** The literal bytes a raw origin writes for this row. */
  wire(): string {
    let head = `HTTP/1.1 ${this.status} ${this.statusText}\r\n`;
    for (const [name, value] of this.headers) {
      head += `${name}: ${value}\r\n`;
    }
    head += `Content-Length: ${Buffer.byteLength(this.body)}\r\n\r\n`;
    return head + this.body;
  }

  /** The equivalent canned `HttpResponse`. */
  response(): HttpResponse {
    return cannedRaw(this.body, {
      status: this.status,
      statusText: this.statusText,
      headers: Object.fromEntries(this.headers),
    });
  }
}

const NEXT_LINK = '<https://api.github.com/repos/o/r/git/refs/tags?page=2>; rel="next"';

/** Rows 1-8 — every adapter, real or canned, must satisfy these. */
export const RESPONSE_CASES: readonly ResponseCase[] = [
  new ResponseCase(
    "json-200",
    200,
    "OK",
    JSON.stringify({ object: { type: "commit", sha: "a".repeat(40) } }),
  ),
  new ResponseCase("html-200", 200, "OK", "<html>not json</html>"),
  new ResponseCase("not-found-404", 404, "Not Found", '{"message": "Not Found"}'),
  new ResponseCase("server-error-500", 500, "Internal Server Error", '{"message": "boom"}'),
  new ResponseCase("link-header", 200, "OK", "[]", [["Link", NEXT_LINK]]),
  new ResponseCase("token-supplied", 200, "OK", "{}", [], "s3cret"),
  new ResponseCase("no-token", 200, "OK", "{}"),
  // Row 8 — a paginated page that parses as JSON but is not an array. The
  // transport resolves this like any other 200; it is `GitHubClient.listTags`
  // (`refNames`, `github.ts`) that must turn it into `ResolveError` rather than
  // truncating the tag list or crashing outright. Binding the raw bytes here
  // keeps both adapters delivering the identical malformed body so that
  // per-port shape-check, which is tested separately, sees the same input.
  new ResponseCase("non-array-page", 200, "OK", '{"message": "not an array"}'),
];

/** Rows 9-14 — a canned double satisfies these by construction, so it skips them. */
export const FAILURE_CASES: readonly string[] = [
  "connection-refused",
  "abrupt-close",
  "stall-mid-body",
  "truncated-body",
  "dribble-body",
  "dribble-head",
];

export const ALL_CASES: ReadonlyArray<ResponseCase | string> = [
  ...RESPONSE_CASES,
  ...FAILURE_CASES,
];

/** Test id for a table row. */
export function caseId(testCase: ResponseCase | string): string {
  return typeof testCase === "string" ? testCase : testCase.name;
}

// ---- the loopback origin ----

/** A head that promises 100 bytes and is followed by 5, used by rows 11 and 12. */
const UNDERDELIVERED = "HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n12345";

/**
 * Row 13's shape: one body byte every `DRIBBLE_INTERVAL_MS` for 10s.
 *
 * The interval must exceed `FAILURE_DEADLINE_MS / 2` so that a *per-socket*
 * timeout of one deadline never fires — which is exactly what makes the row
 * distinguish a wall-clock deadline from a per-operation one.
 */
const DRIBBLE_INTERVAL_MS = 200;
const DRIBBLE_LENGTH = 50;

type Handler = (socket: Socket) => void;

/**
 * A raw-socket origin bound to `127.0.0.1:0`.
 *
 * Teardown destroys every tracked socket before `close()`: a connection with an
 * in-flight request the handler never answers (row 11) blocks the `close`
 * callback indefinitely otherwise.
 */
export class LoopbackOrigin {
  private readonly server: Server;
  private readonly sockets = new Set<Socket>();
  readonly requests: string[] = [];
  private port = 0;

  constructor(handler: Handler) {
    this.server = createServer((socket) => {
      this.sockets.add(socket);
      socket.on("close", () => this.sockets.delete(socket));
      socket.on("error", () => {}); // the client hanging up is not a failure
      let head = "";
      const onData = (chunk: Buffer): void => {
        head += chunk.toString("latin1");
        if (head.includes("\r\n\r\n")) {
          socket.off("data", onData);
          this.requests.push(head);
          handler(socket);
        }
      };
      socket.on("data", onData);
    });
  }

  async start(): Promise<void> {
    await new Promise<void>((resolve) => this.server.listen(0, "127.0.0.1", resolve));
    this.port = (this.server.address() as AddressInfo).port;
  }

  /** A URL this origin will answer. */
  get url(): string {
    return `http://127.0.0.1:${this.port}/contract`;
  }

  /** The `Authorization` header value the origin saw, if any. */
  observedAuth(): string | null {
    return authHeader(this.requests[this.requests.length - 1] ?? "");
  }

  async stop(): Promise<void> {
    for (const socket of this.sockets) {
      socket.destroy();
    }
    await new Promise<void>((resolve) => this.server.close(() => resolve()));
  }
}

/** Extract the `Authorization` value from a raw request head. */
function authHeader(request: string): string | null {
  for (const line of request.split("\r\n")) {
    const idx = line.indexOf(":");
    if (idx > 0 && line.slice(0, idx).trim().toLowerCase() === "authorization") {
      return line.slice(idx + 1).trim();
    }
  }
  return null;
}

const FAILURE_HANDLERS: Record<string, Handler | null> = {
  // Served by a port nobody listens on.
  "connection-refused": null,
  /** Row 10 — accept the request, then close without writing a response. */
  "abrupt-close": (socket) => socket.end(),
  /** Row 11 — send a head and part of the body, then hold the connection. */
  "stall-mid-body": (socket) => {
    socket.write(UNDERDELIVERED);
  },
  /** Row 12 — declare 100 bytes, deliver 5, close. */
  "truncated-body": (socket) => {
    socket.write(UNDERDELIVERED);
    socket.end();
  },
  /**
   * Row 13 — send one body byte every 200ms for 10s.
   *
   * The row rows 11 and 12 cannot express. A *stalled* peer is caught by a
   * per-socket-operation timeout too, because no operation completes; a peer
   * that keeps trickling resets that timeout forever, so only an adapter
   * honouring a genuine **wall-clock** deadline aborts. `AbortSignal.timeout`
   * is one; `urlopen(timeout=)` alone is not.
   */
  "dribble-body": (socket) => {
    socket.write(`HTTP/1.1 200 OK\r\nContent-Length: ${DRIBBLE_LENGTH}\r\n\r\n`);
    let sent = 0;
    const timer = setInterval(() => {
      if (sent++ >= DRIBBLE_LENGTH || socket.destroyed) {
        clearInterval(timer);
        return;
      }
      socket.write("x");
    }, DRIBBLE_INTERVAL_MS);
    timer.unref();
    socket.on("close", () => clearInterval(timer));
  },
  /**
   * Row 14 — send one head byte every 200ms for 10s, never completing it.
   *
   * `dribble-body` (row 13) proves a wall-clock deadline once the head is
   * already in hand; this row proves the same thing about the head itself —
   * no status line, no headers, ever, just a trickle that a per-operation
   * timeout renews forever. An adapter that only starts its deadline once it
   * sees body bytes — the exact gap a fix for row 13 alone could leave open —
   * hangs on this row instead of failing it.
   */
  "dribble-head": (socket) => {
    let sent = 0;
    const timer = setInterval(() => {
      if (sent++ >= DRIBBLE_LENGTH || socket.destroyed) {
        clearInterval(timer);
        return;
      }
      socket.write("H");
    }, DRIBBLE_INTERVAL_MS);
    timer.unref();
    socket.on("close", () => clearInterval(timer));
  },
};

/** A URL on a loopback port that nothing is listening on. */
async function closedPortUrl(): Promise<string> {
  const origin = new LoopbackOrigin(() => {});
  await origin.start();
  const { url } = origin;
  await origin.stop();
  return url;
}

// ---- adapter factories ----

/** An adapter bound to one scenario: the client, the URL, the origin's view. */
export interface Bound {
  client: HttpClient;
  url: string;
  observedAuth(): string | null;
}

/** `makeAdapter(case, deadlineMs, body)` runs `body` against a bound adapter. */
export type MakeAdapter = (
  testCase: ResponseCase | string,
  deadlineMs: number,
  body: (bound: Bound) => Promise<void>,
) => Promise<void>;

/**
 * Run a *real* adapter against a raw loopback origin.
 *
 * `build(deadlineMs)` constructs the adapter under test with that wall-clock
 * deadline — the deadline argument's sole caller.
 */
export function loopbackAdapter(build: (deadlineMs: number) => HttpClient): MakeAdapter {
  return async (testCase, deadlineMs, body) => {
    if (typeof testCase === "string" && FAILURE_HANDLERS[testCase] === null) {
      const url = await closedPortUrl();
      await body({ client: build(deadlineMs), url, observedAuth: () => null });
      return;
    }
    const handler =
      typeof testCase === "string" ? FAILURE_HANDLERS[testCase]! : responder(testCase.wire());
    const origin = new LoopbackOrigin(handler);
    await origin.start();
    try {
      await body({
        client: build(deadlineMs),
        url: origin.url,
        observedAuth: () => origin.observedAuth(),
      });
    } finally {
      await origin.stop();
    }
  };
}

function responder(wire: string): Handler {
  return (socket) => {
    socket.write(wire);
  };
}

/** Run `FakeTransport` against the same table (response rows only). */
export function cannedAdapter(): MakeAdapter {
  return async (testCase, _deadlineMs, body) => {
    if (typeof testCase === "string") {
      throw new Error("a canned double satisfies rows 9-12 by construction; it runs rows 1-8");
    }
    const transport = new FakeTransport({ "/contract": testCase.response() });
    await body({
      client: transport,
      url: "https://origin.test/contract",
      observedAuth: () => {
        const token = transport.tokens[transport.tokens.length - 1];
        return token ? `Bearer ${token}` : null;
      },
    });
  };
}

// ---- the runner ----

/**
 * Assert that `makeAdapter`'s adapter satisfies the conformance table.
 *
 * Defaults to the full table; the test module passes one row at a time so a
 * failure names the row.
 */
export async function runTransportContract(
  makeAdapter: MakeAdapter,
  cases: ReadonlyArray<ResponseCase | string> = ALL_CASES,
): Promise<void> {
  for (const testCase of cases) {
    if (typeof testCase === "string") {
      await assertFailureCase(makeAdapter, testCase);
    } else {
      await assertResponseCase(makeAdapter, testCase);
    }
  }
}

async function assertResponseCase(makeAdapter: MakeAdapter, testCase: ResponseCase): Promise<void> {
  await makeAdapter(testCase, RESPONSE_DEADLINE_MS, async (bound) => {
    const resp = await bound.client.get(bound.url, { token: testCase.token });
    expect(resp.status).toBe(testCase.status);
    expect(resp.body).toBe(testCase.body);
    expect(resp.statusText).toBe(testCase.statusText);
    for (const [name, value] of testCase.headers) {
      expect(resp.header(name.toLowerCase())).toBe(value);
      expect(resp.header(name.toUpperCase())).toBe(value);
    }
    expect(bound.observedAuth()).toBe(testCase.token ? `Bearer ${testCase.token}` : null);
  });
}

async function assertFailureCase(makeAdapter: MakeAdapter, name: string): Promise<void> {
  await makeAdapter(name, FAILURE_DEADLINE_MS, async (bound) => {
    const started = Date.now();
    await expect(bound.client.get(bound.url)).rejects.toBeInstanceOf(TransportError);
    const elapsed = Date.now() - started;
    expect(elapsed, `${name}: deadline was ${FAILURE_DEADLINE_MS}ms`).toBeLessThan(
      FAILURE_CEILING_MS,
    );
  });
}
