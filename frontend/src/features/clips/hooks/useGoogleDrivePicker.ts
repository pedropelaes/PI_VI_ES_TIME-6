import { useCallback, useEffect, useRef, useState } from "react";

export interface GoogleDriveFile {
  id: string;
  name: string;
  mimeType: string;
  sizeBytes?: number;
  durationMillis?: number;
  token: string;
}

declare global {
  interface Window {
    gapi?: any;
    google?: any;
  }
}

const GAPI_SCRIPT_URL = "https://apis.google.com/js/api.js";
const GIS_SCRIPT_URL = "https://accounts.google.com/gsi/client";
const DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file";
const VIDEO_MIME_TYPES = "video/mp4,video/quicktime,video/x-msvideo,video/webm,video/x-matroska";

let gapiScriptPromise: Promise<void> | null = null;
let gisScriptPromise: Promise<void> | null = null;
let pickerLibPromise: Promise<void> | null = null;

export function resetGooglePickerCache() {
  gapiScriptPromise = null;
  gisScriptPromise = null;
  pickerLibPromise = null;
}

function loadScript(src: string, isAvailable?: () => boolean): Promise<void> {
  return new Promise((resolve, reject) => {
    if (isAvailable && isAvailable()) {
      resolve();
      return;
    }

    const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
    if (existing) {
      if (existing.dataset.loaded === "true" || (isAvailable && isAvailable())) {
        resolve();
        return;
      }
      existing.addEventListener("load", () => {
        existing.dataset.loaded = "true";
        resolve();
      });
      existing.addEventListener("error", () => {
        reject(new Error(`Falha ao carregar script do Google: ${src}`));
      });
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      script.dataset.loaded = "true";
      resolve();
    };
    script.onerror = () => reject(new Error(`Falha ao carregar script do Google: ${src}`));
    document.body.appendChild(script);
  });
}

function loadGapiScript(): Promise<void> {
  if (typeof window !== "undefined" && window.gapi) {
    return Promise.resolve();
  }
  if (!gapiScriptPromise) {
    gapiScriptPromise = loadScript(GAPI_SCRIPT_URL, () => !!window.gapi).catch((err) => {
      gapiScriptPromise = null;
      throw err;
    });
  }
  return gapiScriptPromise;
}

function loadGisScript(): Promise<void> {
  if (typeof window !== "undefined" && window.google?.accounts?.oauth2) {
    return Promise.resolve();
  }
  if (!gisScriptPromise) {
    gisScriptPromise = loadScript(GIS_SCRIPT_URL, () => !!window.google?.accounts?.oauth2).catch((err) => {
      gisScriptPromise = null;
      throw err;
    });
  }
  return gisScriptPromise;
}

function loadGooglePickerLib(): Promise<void> {
  if (typeof window !== "undefined" && window.google?.picker) {
    return Promise.resolve();
  }
  if (pickerLibPromise) {
    return pickerLibPromise;
  }
  pickerLibPromise = new Promise<void>((resolve, reject) => {
    loadGapiScript()
      .then(() => {
        if (!window.gapi) {
          throw new Error("GAPI não inicializado.");
        }
        if (window.google?.picker) {
          resolve();
          return;
        }
        window.gapi.load("picker", {
          callback: () => {
            resolve();
          },
          onerror: () => {
            pickerLibPromise = null;
            reject(new Error("Falha ao carregar biblioteca do Google Picker."));
          },
        });
      })
      .catch((err) => {
        pickerLibPromise = null;
        reject(err);
      });
  });
  return pickerLibPromise;
}

function loadGisClient(): Promise<void> {
  if (typeof window !== "undefined" && window.google?.accounts?.oauth2) {
    return Promise.resolve();
  }
  return loadGisScript().then(() => {
    if (window.google?.accounts?.oauth2) {
      return;
    }
    return new Promise<void>((resolve, reject) => {
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        if (window.google?.accounts?.oauth2) {
          clearInterval(interval);
          resolve();
        } else if (attempts > 30) {
          clearInterval(interval);
          reject(new Error("Google Identity Services não inicializado a tempo."));
        }
      }, 50);
    });
  });
}

export function useGoogleDrivePicker() {
  const [pickerReady, setPickerReady] = useState(false);
  const [pickerError, setPickerError] = useState<string | null>(null);

  const tokenClientRef = useRef<any>(null);
  const accessTokenRef = useRef<string | null>(null);
  const activeCallbacksRef = useRef<{
    onSuccess: ((tokenResponse: any) => void) | null;
    onError: ((error: any) => void) | null;
  }>({
    onSuccess: null,
    onError: null,
  });

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const apiKey = import.meta.env.VITE_GOOGLE_API_KEY || "";
  const appId = import.meta.env.VITE_GOOGLE_APP_ID || "";

  // 1. Carrega scripts oficiais do Google (GAPI e GIS) com singleton promises resistentes a F5 e React StrictMode
  useEffect(() => {
    let isMounted = true;

    async function initScripts() {
      try {
        await Promise.all([loadGooglePickerLib(), loadGisClient()]);
        if (!isMounted) return;

        // Inicializa GIS Token Client se ainda não criado
        if (window.google?.accounts?.oauth2 && clientId && !tokenClientRef.current) {
          tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
            client_id: clientId,
            scope: DRIVE_FILE_SCOPE,
            callback: (resp: any) => {
              if (activeCallbacksRef.current.onSuccess) {
                activeCallbacksRef.current.onSuccess(resp);
              }
            },
            error_callback: (err: any) => {
              if (activeCallbacksRef.current.onError) {
                activeCallbacksRef.current.onError(err);
              }
            },
          });
        }

        if (isMounted) {
          setPickerReady(true);
        }
      } catch (err: any) {
        if (isMounted) {
          setPickerError(err.message || "Erro ao carregar SDKs do Google.");
        }
      }
    }

    initScripts();

    return () => {
      isMounted = false;
    };
  }, [clientId]);

  // 2. Função para abrir o Picker oficial do Google
  const openPicker = useCallback((): Promise<GoogleDriveFile | null> => {
    setPickerError(null);

    return new Promise(async (resolve, reject) => {
      if (!clientId || !apiKey) {
        const msg = "Credenciais do Google não configuradas. Verifique as variáveis de ambiente.";
        setPickerError(msg);
        reject(new Error(msg));
        return;
      }

      // Em ambiente de execução real, se ainda estiver inicializando, aguarda
      if (import.meta.env.MODE !== "test") {
        if (!window.google?.picker || !window.google?.accounts?.oauth2) {
          try {
            await Promise.all([loadGooglePickerLib(), loadGisClient()]);
            setPickerReady(true);
          } catch (err: any) {
            const msg = err.message || "Google Picker ainda não está pronto. Tente novamente em alguns instantes.";
            setPickerError(msg);
            reject(new Error(msg));
            return;
          }
        }
      }

      if (!window.google?.picker) {
        const msg = "Google Picker ainda não está pronto. Tente novamente em alguns instantes.";
        setPickerError(msg);
        reject(new Error(msg));
        return;
      }

      function createAndShowPicker(token: string) {
        try {
          const docsView = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
            .setMimeTypes(VIDEO_MIME_TYPES)
            .setMode(window.google.picker.DocsViewMode.LIST);

          const builder = new window.google.picker.PickerBuilder()
            .setAppId(appId)
            .setOAuthToken(token)
            .setDeveloperKey(apiKey)
            .addView(docsView)
            .setTitle("Selecione um vídeo da sua partida no Google Drive")
            .setCallback((data: any) => {
              if (data.action === window.google.picker.Action.PICKED) {
                const doc = data.docs?.[0];
                if (!doc) {
                  resolve(null);
                  return;
                }
                const docDuration = doc.durationMillis
                  ? Number(doc.durationMillis)
                  : doc.lengthSeconds
                  ? Number(doc.lengthSeconds) * 1000
                  : undefined;
                resolve({
                  id: doc.id,
                  name: doc.name,
                  mimeType: doc.mimeType,
                  sizeBytes: doc.sizeBytes ? Number(doc.sizeBytes) : undefined,
                  durationMillis: docDuration,
                  token,
                });
              } else if (data.action === window.google.picker.Action.CANCEL) {
                resolve(null);
              }
            });

          const picker = builder.build();
          picker.setVisible(true);
        } catch (err: any) {
          const msg = err.message || "Erro ao inicializar o seletor do Google Drive.";
          setPickerError(msg);
          reject(new Error(msg));
        }
      }

      // Se já possuímos token válido, abre direto
      if (accessTokenRef.current) {
        createAndShowPicker(accessTokenRef.current);
        return;
      }

      // Garante inicialização do Token Client
      if (!tokenClientRef.current) {
        if (window.google?.accounts?.oauth2) {
          tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
            client_id: clientId,
            scope: DRIVE_FILE_SCOPE,
            callback: (resp: any) => {
              if (activeCallbacksRef.current.onSuccess) {
                activeCallbacksRef.current.onSuccess(resp);
              }
            },
            error_callback: (err: any) => {
              if (activeCallbacksRef.current.onError) {
                activeCallbacksRef.current.onError(err);
              }
            },
          });
        } else {
          const msg = "Google Identity Services não inicializado.";
          setPickerError(msg);
          reject(new Error(msg));
          return;
        }
      }

      let isFinished = false;

      const cleanup = () => {
        isFinished = true;
        activeCallbacksRef.current.onSuccess = null;
        activeCallbacksRef.current.onError = null;
      };

      const handleSuccess = (tokenResponse: any) => {
        if (isFinished) return;
        cleanup();

        if (tokenResponse.error) {
          const msg = tokenResponse.error_description || "Autenticação com o Google cancelada ou negada.";
          setPickerError(msg);
          reject(new Error(msg));
          return;
        }

        const token = tokenResponse.access_token;
        accessTokenRef.current = token;
        createAndShowPicker(token);
      };

      const handleError = (err: any) => {
        if (isFinished) return;
        cleanup();

        if (err?.type === "popup_closed") {
          // Usuário fechou o pop-up de login do Google voluntariamente: cancela suavemente retornando null
          resolve(null);
          return;
        }

        if (err?.type === "popup_blocked") {
          const msg = "A janela de login do Google foi bloqueada pelo navegador. Permita pop-ups para este site.";
          setPickerError(msg);
          reject(new Error(msg));
          return;
        }

        const msg = err?.message || err?.error || "Autenticação com o Google cancelada ou indisponível.";
        setPickerError(msg);
        reject(new Error(msg));
      };

      // Registra callbacks dinâmicos tanto no ref quanto nas propriedades do objeto client
      activeCallbacksRef.current.onSuccess = handleSuccess;
      activeCallbacksRef.current.onError = handleError;

      tokenClientRef.current.callback = handleSuccess;
      tokenClientRef.current.error_callback = handleError;

      // Abre pop-up de consentimento OAuth do Google
      try {
        tokenClientRef.current.requestAccessToken({ prompt: "" });
      } catch (err: any) {
        cleanup();
        const msg = err.message || "Erro ao solicitar autenticação com o Google.";
        setPickerError(msg);
        reject(new Error(msg));
      }
    });
  }, [apiKey, appId, clientId]);

  return {
    openPicker,
    isReady: pickerReady,
    error: pickerError,
  };
}
