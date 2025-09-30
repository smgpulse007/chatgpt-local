import type { VisemeEventPayload } from "./viseme-mapping";

interface SessionHandlers {
  onVisemes: (events: VisemeEventPayload[]) => void;
  onCaption: (text: string) => void;
  onSpeaking: (active: boolean) => void;
  onMicActive: (active: boolean) => void;
}

export interface RealtimeSession {
  pc: RTCPeerConnection;
  close: () => Promise<void>;
}

const SERVER_URL = (import.meta.env.VITE_SERVER_URL as string) ?? "http://localhost:8000";

export async function createRealtimeSession(handlers: SessionHandlers): Promise<RealtimeSession> {
  const pc = new RTCPeerConnection({
    iceServers: []
  });

  const localStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    },
    video: false
  });
  handlers.onMicActive(true);

  localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));

  const audioEl = new Audio();
  audioEl.autoplay = true;
  audioEl.playsInline = true;

  pc.addEventListener("track", (event) => {
    if (event.streams[0]) {
      audioEl.srcObject = event.streams[0];
    }
  });

  let visemeChannel: RTCDataChannel | null = null;

  pc.ondatachannel = (event) => {
    if (event.channel.label !== "visemes") {
      return;
    }
    visemeChannel = event.channel;
    visemeChannel.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.type === "visemes") {
          handlers.onVisemes(data.events ?? []);
        } else if (data.type === "caption") {
          handlers.onCaption(data.text ?? "");
        } else if (data.type === "clear") {
          handlers.onVisemes([]);
        }
      } catch (err) {
        console.error("Failed to parse viseme message", err);
      }
    };
  };

  pc.onconnectionstatechange = () => {
    const state = pc.connectionState;
    handlers.onSpeaking(state === "connected");
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const res = await fetch(`${SERVER_URL}/webrtc/offer`, {
    method: "POST",
    headers: { "Content-Type": "application/sdp" },
    body: offer.sdp ?? ""
  });

  const answerSdp = await res.text();
  const answer = {
    type: "answer" as const,
    sdp: answerSdp
  };
  await pc.setRemoteDescription(answer);

  return {
    pc,
    close: async () => {
      handlers.onMicActive(false);
      visemeChannel?.close();
      pc.getSenders().forEach((sender) => sender.track?.stop());
      pc.close();
    }
  };
}
