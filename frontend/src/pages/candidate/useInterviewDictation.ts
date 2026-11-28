import { useEffect, useRef, useState } from "react";
import { interviewsApi } from "../../api/client";

export const ANSWER_LIMIT = 4000;

interface SpeechSession {
  request: AbortController;
  stream?: MediaStream;
  socket?: WebSocket;
  recorder?: MediaRecorder;
  timeout?: number;
}

interface TranscriptResult {
  type: string;
  is_final?: boolean;
  channel?: { alternatives?: { transcript?: string }[] };
}

const streamUrl = "wss://api.deepgram.com/v1/listen?" + new URLSearchParams({
  model: "nova-3",
  language: "multi",
  interim_results: "true",
  smart_format: "true",
  endpointing: "10",
});

function release(session: SpeechSession) {
  window.clearTimeout(session.timeout);
  session.request.abort();
  if (session.recorder?.state === "recording") session.recorder.stop();
  session.stream?.getTracks().forEach((track) => track.stop());
  if (session.socket && session.socket.readyState < WebSocket.CLOSING) session.socket.close();
}

export function useInterviewDictation(appendTranscript: (text: string) => void) {
  const active = useRef<SpeechSession | null>(null);
  const [phase, setPhase] = useState<"idle" | "connecting" | "listening" | "stopping">("idle");
  const [message, setMessage] = useState("");
  const [interimText, setInterimText] = useState("");
  const supported = typeof MediaRecorder !== "undefined"
    && typeof WebSocket !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);

  useEffect(() => () => {
    const session = active.current;
    active.current = null;
    if (session) release(session);
  }, []);

  function finish(session: SpeechSession, message: string) {
    if (active.current !== session) return;
    active.current = null;
    release(session);
    setInterimText("");
    setPhase("idle");
    setMessage(message);
  }

  function cancel() {
    if (active.current) finish(active.current, "");
    setMessage("");
  }

  async function toggle() {
    const previous = active.current;
    if (previous) {
      if (previous.recorder?.state === "recording") {
        setPhase("stopping");
        window.clearTimeout(previous.timeout);
        previous.timeout = window.setTimeout(() =>
          finish(previous, "Deepgram chưa trả xong bản chép lời. Hãy kiểm tra phần chữ đã nhận."), 8000);
        previous.recorder.stop();
        previous.stream?.getTracks().forEach((track) => track.stop());
      }
      return;
    }
    if (!supported) return;

    const session: SpeechSession = { request: new AbortController() };
    active.current = session;
    setPhase("connecting");
    setMessage("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (active.current !== session) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      session.stream = stream;
      const mimeType = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus"]
        .find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      session.recorder = recorder;
      const { accessToken } = await interviewsApi.speechToken(session.request.signal);
      if (active.current !== session) return;

      const socket = new WebSocket(streamUrl, ["bearer", accessToken]);
      session.socket = socket;
      let hasTranscript = false;
      let ending = false;
      session.timeout = window.setTimeout(() =>
        finish(session, "Kết nối Deepgram hết thời gian chờ. Hãy thử lại."), 10000);

      recorder.ondataavailable = ({ data }) => {
        if (active.current === session && data.size && socket.readyState === WebSocket.OPEN) socket.send(data);
      };
      recorder.onstop = () => {
        if (active.current !== session || socket.readyState !== WebSocket.OPEN) return;
        ending = true;
        socket.send(JSON.stringify({ type: "CloseStream" }));
      };
      recorder.onerror = () => finish(session, "Không thu được âm thanh từ micro. Hãy thử lại.");
      socket.onopen = () => {
        if (active.current !== session) return;
        window.clearTimeout(session.timeout);
        recorder.start(250);
        setPhase("listening");
      };
      socket.onmessage = ({ data }) => {
        if (active.current !== session) return;
        const result = JSON.parse(data) as TranscriptResult;
        if (result.type !== "Results") return;
        const text = result.channel?.alternatives?.[0]?.transcript?.trim() ?? "";
        setInterimText(result.is_final ? "" : text);
        if (result.is_final && text) {
          appendTranscript(text);
          hasTranscript = true;
        }
      };
      socket.onerror = () => finish(session, "Không kết nối được Deepgram. Hãy thử lại hoặc nhập bằng bàn phím.");
      socket.onclose = ({ wasClean }) => {
        const message = ending && wasClean
          ? hasTranscript ? "Kiểm tra và chỉnh bản chép lời trước khi nộp." : "Chưa nhận được lời nói. Hãy thử lại."
          : "Kết nối Deepgram đã ngắt. Hãy kiểm tra phần chữ đã nhận.";
        finish(session, message);
      };
    } catch (error) {
      const message = error instanceof DOMException && error.name === "NotAllowedError"
        ? "Hãy cấp quyền micro rồi thử lại."
        : error instanceof Error ? error.message : "Không thể bật nhận dạng giọng nói.";
      finish(session, message);
    }
  }

  return { supported, phase, message, interimText, toggle, cancel };
}
