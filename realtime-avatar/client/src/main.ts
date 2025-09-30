import { initUI } from "./ui";
import { AvatarController } from "./avatar";
import { createRealtimeSession } from "./webrtc";

const canvas = document.getElementById("scene") as HTMLCanvasElement;
const caption = document.getElementById("caption") as HTMLDivElement;
const micIndicator = document.getElementById("mic-indicator") as HTMLDivElement;

const avatar = new AvatarController(canvas, caption);

const ui = initUI({
  onConnect: async () => {
    const session = await createRealtimeSession({
      onVisemes: (events) => avatar.queueVisemes(events),
      onCaption: (text) => avatar.setCaption(text),
      onSpeaking: (speaking) => avatar.setSpeaking(speaking),
      onMicActive: (active) => micIndicator.style.background = active ? "#22c55e" : "#dc2626"
    });
    avatar.attachSession(session);
    return session;
  },
  onDisconnect: async (session) => {
    await session?.close();
    avatar.detachSession();
  }
});

avatar.start();

window.addEventListener("beforeunload", () => {
  ui.dispose();
});
