import type { RealtimeSession } from "./webrtc";

interface UIOptions {
  onConnect: () => Promise<RealtimeSession>;
  onDisconnect: (session: RealtimeSession | null) => Promise<void>;
}

export function initUI(options: UIOptions) {
  const connectBtn = document.getElementById("connect") as HTMLButtonElement;
  const disconnectBtn = document.getElementById("disconnect") as HTMLButtonElement;
  let session: RealtimeSession | null = null;

  const setBusy = (busy: boolean) => {
    connectBtn.disabled = busy;
    disconnectBtn.disabled = busy || !session;
  };

  const handleConnect = async () => {
    if (session) {
      return;
    }
    setBusy(true);
    try {
      session = await options.onConnect();
    } finally {
      setBusy(false);
      disconnectBtn.disabled = !session;
    }
  };

  const handleDisconnect = async () => {
    if (!session) {
      return;
    }
    setBusy(true);
    try {
      await options.onDisconnect(session);
      session = null;
    } finally {
      setBusy(false);
      disconnectBtn.disabled = true;
    }
  };

  connectBtn.addEventListener("click", handleConnect);
  disconnectBtn.addEventListener("click", handleDisconnect);

  return {
    dispose: () => {
      connectBtn.removeEventListener("click", handleConnect);
      disconnectBtn.removeEventListener("click", handleDisconnect);
    }
  };
}
