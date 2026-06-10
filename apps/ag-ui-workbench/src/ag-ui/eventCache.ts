import type { AgUiEvent, RawTimelineEntry } from "./types";

const DB_NAME = "houmao-ag-ui-workbench-events";
const DB_VERSION = 1;
const STORE_NAME = "events";
const TARGET_INDEX = "targetKey";
const MAX_EVENTS_PER_TARGET = 500;

export interface CachedAgUiEventRecord {
  id: string;
  targetKey: string;
  threadId: string;
  sequence: number;
  receivedAt: string;
  sseEventId?: string;
  event: AgUiEvent;
  raw: RawTimelineEntry;
}

export async function loadCachedEvents(targetKey: string): Promise<CachedAgUiEventRecord[]> {
  const db = await openEventDb();
  const transaction = db.transaction(STORE_NAME, "readonly");
  const index = transaction.objectStore(STORE_NAME).index(TARGET_INDEX);
  const records = await requestToPromise<CachedAgUiEventRecord[]>(index.getAll(targetKey));
  db.close();
  return records.sort((left, right) => left.sequence - right.sequence);
}

export async function appendCachedEvent(record: CachedAgUiEventRecord): Promise<void> {
  const db = await openEventDb();
  const transaction = db.transaction(STORE_NAME, "readwrite");
  transaction.objectStore(STORE_NAME).put(record);
  await transactionDone(transaction);
  db.close();
  await pruneCachedEvents(record.targetKey, MAX_EVENTS_PER_TARGET);
}

export async function clearCachedEvents(targetKey?: string): Promise<void> {
  const db = await openEventDb();
  if (!targetKey) {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    transaction.objectStore(STORE_NAME).clear();
    await transactionDone(transaction);
    db.close();
    return;
  }
  const records = await loadCachedEvents(targetKey);
  const transaction = db.transaction(STORE_NAME, "readwrite");
  const store = transaction.objectStore(STORE_NAME);
  for (const record of records) {
    store.delete(record.id);
  }
  await transactionDone(transaction);
  db.close();
}

export function cachedRecordId(targetKey: string, sequence: number): string {
  return `${targetKey}:${sequence}`;
}

async function pruneCachedEvents(targetKey: string, limit: number): Promise<void> {
  const records = await loadCachedEvents(targetKey);
  const excess = records.length - limit;
  if (excess <= 0) {
    return;
  }
  const db = await openEventDb();
  const transaction = db.transaction(STORE_NAME, "readwrite");
  const store = transaction.objectStore(STORE_NAME);
  for (const record of records.slice(0, excess)) {
    store.delete(record.id);
  }
  await transactionDone(transaction);
  db.close();
}

function openEventDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB is unavailable."));
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      const store = db.objectStoreNames.contains(STORE_NAME)
        ? request.transaction!.objectStore(STORE_NAME)
        : db.createObjectStore(STORE_NAME, { keyPath: "id" });
      if (!store.indexNames.contains(TARGET_INDEX)) {
        store.createIndex(TARGET_INDEX, "targetKey", { unique: false });
      }
    };
    request.onerror = () => reject(request.error ?? new Error("IndexedDB open failed."));
    request.onsuccess = () => resolve(request.result);
  });
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed."));
    request.onsuccess = () => resolve(request.result);
  });
}

function transactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error("IndexedDB transaction failed."));
    transaction.onabort = () => reject(transaction.error ?? new Error("IndexedDB transaction aborted."));
  });
}
