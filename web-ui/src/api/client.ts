import type { WhisperConfig, WhisperStatus, DiagnosticInfo } from './types';

const API_BASE = '/api';

export async function fetchConfig(): Promise<WhisperConfig> {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error(`Failed to fetch config: ${res.statusText}`);
  return res.json();
}

export async function saveConfig(config: WhisperConfig): Promise<WhisperConfig> {
  const res = await fetch(`${API_BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!res.ok) throw new Error(`Failed to save config: ${res.statusText}`);
  return res.json();
}

export async function getStatus(): Promise<WhisperStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error(`Failed to get status: ${res.statusText}`);
  return res.json();
}

export async function startDaemon(): Promise<{ started: boolean; pid: number }> {
  const res = await fetch(`${API_BASE}/daemon/start`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to start daemon: ${res.statusText}`);
  return res.json();
}

export async function stopDaemon(): Promise<{ stopped: boolean }> {
  const res = await fetch(`${API_BASE}/daemon/stop`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to stop daemon: ${res.statusText}`);
  return res.json();
}

export async function getSources(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/sources`);
  if (!res.ok) throw new Error(`Failed to get sources: ${res.statusText}`);
  return res.json();
}

export async function getDiagnostics(): Promise<DiagnosticInfo> {
  const res = await fetch(`${API_BASE}/diagnostics`);
  if (!res.ok) throw new Error(`Failed to get diagnostics: ${res.statusText}`);
  return res.json();
}

export function connectEvents(onMessage: (event: Event) => void, onError: (err: Event) => void): EventSource {
  const es = new EventSource(`${API_BASE}/events`);
  es.onmessage = onMessage;
  es.onerror = onError;
  return es;
}

export interface ServerMessageEvent {
  event: string;
  data: unknown;
}
