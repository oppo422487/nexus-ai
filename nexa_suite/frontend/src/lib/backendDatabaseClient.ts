import { DEFAULT_BACKEND_URL } from "./backendCommandClient";

export type BackendDatabaseStatusResponse = {
  status: string;
  module: string;
  phase: string;
  database_enabled: boolean;
  database_mode: string;
  database_path: string;
  migrations_enabled: boolean;
  reads_enabled: boolean;
  writes_enabled: boolean;
  reason: string;
  execution_enabled: boolean;
};

export async function getBackendDatabaseStatus(
  backendUrl = DEFAULT_BACKEND_URL,
): Promise<BackendDatabaseStatusResponse> {
  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/database/status`);
  } catch {
    throw new Error(
      `Failed to reach backend database status at ${backendUrl}/api/database/status`,
    );
  }

  if (!response.ok) {
    throw new Error(
      `Backend database status request failed with status ${response.status}`,
    );
  }

  return response.json() as Promise<BackendDatabaseStatusResponse>;
}
