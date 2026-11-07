import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createJobFromGoogleDrive } from "./api";

describe("createJobFromGoogleDrive", () => {
  beforeEach(() => {
    localStorage.setItem("access_token", "app-token-123");
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("envia payload correto com header de autorização e devolve job_id", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ job_id: "job-abc-123", status: "DOWNLOADING" }), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      })
    );

    const payload = {
      fileId: "drive-file-001",
      googleAccessToken: "ya29.sample",
      targetNumber: 10,
      startTs: 0,
      endTs: 120,
    };

    const res = await createJobFromGoogleDrive(payload);

    expect(res).toEqual({ job_id: "job-abc-123", status: "DOWNLOADING" });
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toContain("/jobs/import/google-drive");
    expect(options?.method).toBe("POST");

    const headers = options?.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer app-token-123");
    expect(headers["Content-Type"]).toBe("application/json");

    const body = JSON.parse(options?.body as string);
    expect(body).toEqual({
      file_id: "drive-file-001",
      google_access_token: "ya29.sample",
      target_number: 10,
      start_ts: 0,
      end_ts: 120,
    });
  });

  it("trata erro 401 de token do Google retornando a mensagem de erro específica", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Token do Google Drive inválido ou expirado." }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      )
    );

    await expect(
      createJobFromGoogleDrive({
        fileId: "f-1",
        googleAccessToken: "ya29.bad",
        targetNumber: 7,
        startTs: 0,
        endTs: 0,
      })
    ).rejects.toThrow("Token do Google Drive inválido ou expirado.");
  });

  it("trata erro 400 de formato ou tamanho de vídeo", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "O arquivo excede o limite máximo permitido de 2048MB." }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    );

    await expect(
      createJobFromGoogleDrive({
        fileId: "f-big",
        googleAccessToken: "ya29.valid",
        targetNumber: 9,
        startTs: 0,
        endTs: 0,
      })
    ).rejects.toThrow("O arquivo excede o limite máximo permitido de 2048MB.");
  });
});

