export {};

declare global {
  interface Window {
    nexa?: {
      platform: string;
      appMode: "desktop";
      backendUrl: string;
    };
  }
}