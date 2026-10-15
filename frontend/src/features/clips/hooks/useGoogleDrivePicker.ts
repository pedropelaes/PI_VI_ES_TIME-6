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

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Falha ao carregar script do Google: ${src}`));
    document.body.appendChild(script);
  });
}

export function useGoogleDrivePicker() {
  const [isGapiLoaded, setIsGapiLoaded] = useState(false);
  const [isGisLoaded, setIsGisLoaded] = useState(false);
  const [pickerReady, setPickerReady] = useState(false);
  const [pickerError, setPickerError] = useState<string | null>(null);

  const tokenClientRef = useRef<any>(null);
  const accessTokenRef = useRef<string | null>(null);

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const apiKey = import.meta.env.VITE_GOOGLE_API_KEY || "";
  const appId = import.meta.env.VITE_GOOGLE_APP_ID || "";

  // 1. Carrega scripts oficiais do Google (GAPI e GIS)
  useEffect(() => {
    let isMounted = true;

    async function initScripts() {
      try {
        await Promise.all([loadScript(GAPI_SCRIPT_URL), loadScript(GIS_SCRIPT_URL)]);
        if (!isMounted) return;

        // Inicializa GAPI Picker
        if (window.gapi) {
          window.gapi.load("picker", () => {
            if (isMounted) setIsGapiLoaded(true);
          });
        }

        // Inicializa GIS Token Client
        if (window.google?.accounts?.oauth2 && clientId) {
          tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
            client_id: clientId,
            scope: DRIVE_FILE_SCOPE,
            callback: () => {}, // Callback sobrescrito em openPicker
          });
          if (isMounted) setIsGisLoaded(true);
        }
      } catch (err: any) {
        if (isMounted) setPickerError(err.message || "Erro ao carregar SDKs do Google.");
      }
    }

    initScripts();

    return () => {
      isMounted = false;
    };
  }, [clientId]);

  useEffect(() => {
    if (isGapiLoaded && isGisLoaded) {
      setPickerReady(true);
    }
  }, [isGapiLoaded, isGisLoaded]);

  // 2. Função para abrir o Picker oficial do Google
  const openPicker = useCallback((): Promise<GoogleDriveFile | null> => {
    setPickerError(null);

    return new Promise((resolve, reject) => {
      if (!clientId || !apiKey) {
        const msg = "Credenciais do Google não configuradas. Verifique as variáveis de ambiente.";
        setPickerError(msg);
        reject(new Error(msg));
        return;
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
                const docDuration = doc.durationMillis ? Number(doc.durationMillis) : (doc.lengthSeconds ? Number(doc.lengthSeconds) * 1000 : undefined);
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

      // Caso contrário, solicita token via Google Identity Services
      if (!tokenClientRef.current) {
        if (window.google?.accounts?.oauth2) {
          tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
            client_id: clientId,
            scope: DRIVE_FILE_SCOPE,
            callback: () => {},
          });
        } else {
          const msg = "Google Identity Services não inicializado.";
          setPickerError(msg);
          reject(new Error(msg));
          return;
        }
      }

      tokenClientRef.current.callback = (tokenResponse: any) => {
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

      // Abre pop-up de consentimento OAuth do Google
      tokenClientRef.current.requestAccessToken({ prompt: "" });
    });
  }, [apiKey, appId, clientId]);

  return {
    openPicker,
    isReady: pickerReady,
    error: pickerError,
  };
}

