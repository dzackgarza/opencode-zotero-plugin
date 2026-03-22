import { describe, expect, it } from "bun:test";
import { spawnSync } from "node:child_process";

function requireEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} must be set (run via \`just test\`)`);
  return value;
}

const BASE_URL = requireEnv("OPENCODE_BASE_URL");
const AGENT_NAME = "plugin-proof";
const PROJECT_DIR = process.cwd();
const MANAGER_PACKAGE = "git+https://github.com/dzackgarza/opencode-manager.git";
const MAX_BUFFER = 8 * 1024 * 1024;
const SESSION_TIMEOUT_MS = 240_000;
const LOCAL_ZOTERO_BASE_URL = "http://127.0.0.1:23119";
const SEEDED_DOI = "10.1038/nature12373";
const IMPORT_DOI = SEEDED_DOI;

type TranscriptStep = {
  type: string;
  tool?: string;
  status?: string;
  outputText?: string;
};

type ZoteroItem = {
  key: string;
  data: {
    DOI?: string;
    title?: string;
    extra?: string;
    collections?: string[];
  };
};

function runOcm(args: string[]) {
  const result = spawnSync(
    "uvx",
    ["--from", MANAGER_PACKAGE, "ocm", ...args],
    {
      env: { ...process.env, OPENCODE_BASE_URL: BASE_URL },
      cwd: PROJECT_DIR,
      encoding: "utf8",
      timeout: SESSION_TIMEOUT_MS,
      maxBuffer: MAX_BUFFER,
    },
  );
  if (result.error) throw result.error;
  const stdout = result.stdout ?? "";
  const stderr = result.stderr ?? "";
  if (result.status !== 0) {
    throw new Error(`ocm ${args.join(" ")} failed\nSTDOUT:\n${stdout}\nSTDERR:\n${stderr}`);
  }
  return { stdout, stderr };
}

function beginSession(prompt: string): string {
  const { stdout } = runOcm(["begin-session", prompt, "--agent", AGENT_NAME, "--json"]);
  const data = JSON.parse(stdout) as { sessionID: string };
  if (!data.sessionID) throw new Error(`begin-session returned no sessionID: ${stdout}`);
  return data.sessionID;
}

function waitIdle(sessionID: string) {
  runOcm(["wait", sessionID, "--timeout-sec=180"]);
}

function deleteSession(sessionID: string) {
  try {
    runOcm(["delete", sessionID]);
  } catch {
    // best-effort cleanup
  }
}

function readTranscriptSteps(sessionID: string): TranscriptStep[] {
  const { stdout } = runOcm(["transcript", sessionID, "--json"]);
  const data = JSON.parse(stdout) as {
    turns: Array<{
      assistantMessages: Array<{ steps: Array<TranscriptStep | null> }>;
    }>;
  };
  return data.turns.flatMap((turn) =>
    turn.assistantMessages.flatMap((msg) =>
      (msg.steps ?? []).filter((step): step is TranscriptStep => step !== null),
    ),
  );
}

function completedToolStep(sessionID: string, toolName: string): TranscriptStep {
  const steps = readTranscriptSteps(sessionID);
  const step = steps.find(
    (candidate) =>
      candidate.type === "tool" &&
      candidate.tool === toolName &&
      candidate.status === "completed",
  );
  if (!step) {
    throw new Error(
      `No completed ${toolName} step found in transcript ${sessionID}\n${JSON.stringify(steps, null, 2)}`,
    );
  }
  return step;
}

function parseToolJson<T>(sessionID: string, toolName: string): T {
  const step = completedToolStep(sessionID, toolName);
  const outputText = step.outputText?.trim();
  if (!outputText) {
    throw new Error(`Tool ${toolName} returned empty output in session ${sessionID}`);
  }
  return JSON.parse(outputText) as T;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${LOCAL_ZOTERO_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed with ${response.status}: ${await response.text()}`);
  }
  return (await response.json()) as T;
}

async function findTopItemsByDoi(doi: string): Promise<ZoteroItem[]> {
  const query = new URLSearchParams({
    format: "json",
    q: doi,
    qmode: "everything",
    limit: "20",
  });
  const items = await fetchJson<ZoteroItem[]>(
    `/api/users/0/items/top?${query.toString()}`,
  );
  return items.filter((item) => item.data.DOI?.trim() === doi);
}

async function readItem(itemKey: string): Promise<ZoteroItem> {
  return fetchJson<ZoteroItem>(`/api/users/0/items/${itemKey}?format=json`);
}

async function readTrashKeys(): Promise<Set<string>> {
  const items = await fetchJson<Array<{ key: string }>>(
    "/api/users/0/items/trash?format=json&limit=100",
  );
  return new Set(items.map((item) => item.key));
}

async function waitFor(predicate: () => Promise<boolean>, message: string) {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await Bun.sleep(250);
  }
  throw new Error(message);
}

describe("opencode-zotero-plugin live e2e", () => {
  it("proves zotero_count returns the live local library size", () => {
    let sessionID: string | undefined;
    try {
      sessionID = beginSession(
        "Call zotero_count exactly once. Reply with ONLY the exact text returned by the tool, nothing else.",
      );
      waitIdle(sessionID);

      const step = completedToolStep(sessionID, "zotero_count");
      const count = Number(step.outputText?.trim());
      expect(Number.isInteger(count)).toBe(true);
      expect(count).toBeGreaterThanOrEqual(1);
    } finally {
      if (sessionID) deleteSession(sessionID);
    }
  }, SESSION_TIMEOUT_MS);

  it("proves zotero_stats summary returns real aggregate data from the local library", () => {
    let sessionID: string | undefined;
    try {
      sessionID = beginSession(
        "Call zotero_stats exactly once with action=summary. Reply with ONLY the exact text returned by the tool, nothing else.",
      );
      waitIdle(sessionID);

      const summary = parseToolJson<{
        total_items: number;
        collections: number;
        item_types: Record<string, number>;
      }>(sessionID, "zotero_stats");

      expect(summary.total_items).toBeGreaterThanOrEqual(1);
      expect(summary.collections).toBeGreaterThanOrEqual(1);
      expect(summary.item_types.journalArticle).toBeGreaterThanOrEqual(1);
    } finally {
      if (sessionID) deleteSession(sessionID);
    }
  }, SESSION_TIMEOUT_MS);

  it("proves import, update, and delete mutate the real local Zotero library", async () => {
    const sessionIDs: string[] = [];
    let importedItemKey: string | undefined;
    try {
      const importSessionID = beginSession(
        `Call the tool named zotero_import exactly once with JSON args {"action":"by_doi","identifier":"${IMPORT_DOI}"}. Reply with ONLY the exact text returned by the tool, nothing else.`,
      );
      sessionIDs.push(importSessionID);
      waitIdle(importSessionID);

      const importResult = parseToolJson<{
        success: boolean;
        operation: string;
        item_key: string;
      }>(importSessionID, "zotero_import");
      expect(importResult.success).toBe(true);
      expect(importResult.operation).toBe("import_by_doi");
      importedItemKey = importResult.item_key;
      expect(importedItemKey).toBeTruthy();

      const proofExtra = `plugin-proof-extra-${Date.now()}`;
      const updateSessionID = beginSession(
        `Call the tool named zotero_update_item exactly once with JSON args {"item_key":"${importedItemKey}","fields":{"extra":"${proofExtra}"}}. Reply with ONLY the exact text returned by the tool, nothing else.`,
      );
      sessionIDs.push(updateSessionID);
      waitIdle(updateSessionID);

      const updateResult = parseToolJson<{
        success: boolean;
        operation: string;
        stage: string;
      }>(updateSessionID, "zotero_update_item");
      expect(updateResult.success).toBe(true);
      expect(updateResult.operation).toBe("update_item_fields");
      expect(updateResult.stage).toBe("completed");

      await waitFor(async () => {
        const item = await readItem(importedItemKey!);
        return item.data.extra === proofExtra;
      }, `Updated extra field did not appear on ${importedItemKey}`);

      const deleteSessionID = beginSession(
        `Call the tool named zotero_delete_items exactly once with JSON args {"item_keys":["${importedItemKey}"]}. Reply with ONLY the exact text returned by the tool, nothing else.`,
      );
      sessionIDs.push(deleteSessionID);
      waitIdle(deleteSessionID);

      const deleteResult = parseToolJson<{
        success: boolean;
        operation: string;
      }>(deleteSessionID, "zotero_delete_items");
      expect(deleteResult.success).toBe(true);
      expect(deleteResult.operation).toBe("delete_item");

      await waitFor(async () => {
        const trashKeys = await readTrashKeys();
        return trashKeys.has(importedItemKey!);
      }, `Deleted item ${importedItemKey} never appeared in trash`);
    } finally {
      for (const sessionID of sessionIDs) {
        deleteSession(sessionID);
      }
    }
  }, SESSION_TIMEOUT_MS);
});
