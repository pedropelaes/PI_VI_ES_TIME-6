import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useGoogleDrivePicker } from "./useGoogleDrivePicker";

describe("useGoogleDrivePicker", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "test-client-id");
    vi.stubEnv("VITE_GOOGLE_API_KEY", "test-api-key");
    vi.stubEnv("VITE_GOOGLE_APP_ID", "test-app-id");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    delete window.gapi;
    delete window.google;
  });

  it("inicializa com estado inicial correto", () => {
    const { result } = renderHook(() => useGoogleDrivePicker());
    expect(result.current.isReady).toBe(false);
    expect(result.current.error).toBeNull();
    expect(typeof result.current.openPicker).toBe("function");
  });

  it("rejeita quando credenciais não estão configuradas", async () => {
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "");
    const { result } = renderHook(() => useGoogleDrivePicker());

    let err: any;
    await act(async () => {
      try {
        await result.current.openPicker();
      } catch (e) {
        err = e;
      }
    });
    expect(err?.message).toContain("Credenciais do Google não configuradas.");
  });

  it("rejeita se Google Picker ainda não carregou", async () => {
    const { result } = renderHook(() => useGoogleDrivePicker());

    let err: any;
    await act(async () => {
      try {
        await result.current.openPicker();
      } catch (e) {
        err = e;
      }
    });
    expect(err?.message).toContain("Google Picker ainda não está pronto.");
  });

  it("abre o Picker quando as APIs estão disponíveis e retorna o arquivo selecionado", async () => {
    const fakeToken = "ya29.fake-token";
    let tokenCallback: any;

    const fakeTokenClient = {
      requestAccessToken: vi.fn(() => {
        tokenCallback({ access_token: fakeToken });
      }),
      set callback(cb: any) {
        tokenCallback = cb;
      },
    };

    let pickerCallback: any;
    const fakePicker = {
      setVisible: vi.fn(),
    };

    const fakePickerBuilder = {
      setAppId: vi.fn().mockReturnThis(),
      setOAuthToken: vi.fn().mockReturnThis(),
      setDeveloperKey: vi.fn().mockReturnThis(),
      addView: vi.fn().mockReturnThis(),
      setTitle: vi.fn().mockReturnThis(),
      setCallback: vi.fn((cb: any) => {
        pickerCallback = cb;
        return fakePickerBuilder;
      }),
      build: vi.fn(() => fakePicker),
    };

    window.google = {
      accounts: {
        oauth2: {
          initTokenClient: vi.fn(() => fakeTokenClient),
        },
      },
      picker: {
        PickerBuilder: vi.fn(() => fakePickerBuilder),
        DocsView: vi.fn().mockImplementation(() => ({
          setMimeTypes: vi.fn().mockReturnThis(),
          setMode: vi.fn().mockReturnThis(),
        })),
        ViewId: { DOCS: "DOCS" },
        DocsViewMode: { LIST: "LIST" },
        Action: { PICKED: "picked", CANCEL: "cancel" },
      },
    };

    window.gapi = {
      load: vi.fn((_name, cb) => cb && cb()),
    };

    const { result } = renderHook(() => useGoogleDrivePicker());

    let file: any;
    await act(async () => {
      const promise = result.current.openPicker();
      pickerCallback({
        action: "picked",
        docs: [
          {
            id: "drive-video-999",
            name: "lance_gol.mp4",
            mimeType: "video/mp4",
            sizeBytes: 10485760,
          },
        ],
      });
      file = await promise;
    });

    expect(fakeTokenClient.requestAccessToken).toHaveBeenCalled();
    expect(fakePicker.setVisible).toHaveBeenCalledWith(true);

    expect(file).toEqual({
      id: "drive-video-999",
      name: "lance_gol.mp4",
      mimeType: "video/mp4",
      sizeBytes: 10485760,
      token: fakeToken,
    });
  });

  it("retorna null quando o usuário cancela o Picker", async () => {
    const fakeToken = "ya29.fake-token";
    let tokenCallback: any;

    const fakeTokenClient = {
      requestAccessToken: vi.fn(() => {
        tokenCallback({ access_token: fakeToken });
      }),
      set callback(cb: any) {
        tokenCallback = cb;
      },
    };

    let pickerCallback: any;
    const fakePicker = {
      setVisible: vi.fn(),
    };

    const fakePickerBuilder = {
      setAppId: vi.fn().mockReturnThis(),
      setOAuthToken: vi.fn().mockReturnThis(),
      setDeveloperKey: vi.fn().mockReturnThis(),
      addView: vi.fn().mockReturnThis(),
      setTitle: vi.fn().mockReturnThis(),
      setCallback: vi.fn((cb: any) => {
        pickerCallback = cb;
        return fakePickerBuilder;
      }),
      build: vi.fn(() => fakePicker),
    };

    window.google = {
      accounts: {
        oauth2: {
          initTokenClient: vi.fn(() => fakeTokenClient),
        },
      },
      picker: {
        PickerBuilder: vi.fn(() => fakePickerBuilder),
        DocsView: vi.fn().mockImplementation(() => ({
          setMimeTypes: vi.fn().mockReturnThis(),
          setMode: vi.fn().mockReturnThis(),
        })),
        ViewId: { DOCS: "DOCS" },
        DocsViewMode: { LIST: "LIST" },
        Action: { PICKED: "picked", CANCEL: "cancel" },
      },
    };

    const { result } = renderHook(() => useGoogleDrivePicker());

    let file: any;
    await act(async () => {
      const promise = result.current.openPicker();
      pickerCallback({ action: "cancel" });
      file = await promise;
    });

    expect(file).toBeNull();
  });
});

