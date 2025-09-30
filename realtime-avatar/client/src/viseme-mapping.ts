export interface VisemeEventPayload {
  t: number;
  viseme: string;
  weight: number;
  blendshapes: Record<string, number>;
}

export function pickBlendshapeWeights(
  schedule: VisemeEventPayload[],
  elapsed: number
): Record<string, number> {
  if (!schedule.length) {
    return {};
  }
  const previous = schedule.filter((event) => event.t <= elapsed).pop();
  if (!previous) {
    return schedule[0].blendshapes;
  }
  const next = schedule.find((event) => event.t > elapsed);
  if (!next) {
    return previous.blendshapes;
  }
  const span = Math.max(next.t - previous.t, 0.001);
  const alpha = Math.min(Math.max((elapsed - previous.t) / span, 0), 1);
  const weights: Record<string, number> = {};
  const keys = new Set([...Object.keys(previous.blendshapes), ...Object.keys(next.blendshapes)]);
  keys.forEach((key) => {
    const start = previous.blendshapes[key] ?? 0;
    const end = next.blendshapes[key] ?? 0;
    weights[key] = start + (end - start) * alpha;
  });
  return weights;
}
