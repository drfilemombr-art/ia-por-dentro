import React from "react";
import { Composition } from "remotion";
import { Abertura } from "./Abertura";
import { Cinema } from "./Cinema";
import timeline from "../data/timeline.json";

export const Root: React.FC = () => (
  <>
  {/* Bloco 1 · prévia com os 2 s finais da abertura na cabeça (avaliar a emenda) e trecho limpo */}
  <Composition id="B01-previa" component={Cinema} width={1080} height={1920} fps={timeline.fps}
    durationInFrames={Math.round(timeline.blocos.b1.fim * timeline.fps) - 276}
    defaultProps={{ from: 276, fadeEnd: false, seam: 336 }} />
  <Composition id="B01" component={Cinema} width={1080} height={1920} fps={timeline.fps}
    durationInFrames={Math.round(timeline.blocos.b1.fim * timeline.fps) - 336}
    defaultProps={{ from: 336, fadeEnd: false, seam: null }} />
  <Composition id="Master" component={Cinema} width={1080} height={1920} fps={timeline.fps}
    durationInFrames={Math.round(timeline.blocos.b1.fim * timeline.fps)}
    defaultProps={{ from: 0, fadeEnd: true, seam: null }} />
  <Composition
    id="Cinema"
    component={Cinema}
    width={1080}
    height={1920}
    fps={timeline.fps}
    durationInFrames={Math.round(timeline.durationSec * timeline.fps)}
  />
  <Composition
    id="Abertura"
    component={Abertura}
    width={1080}
    height={1920}
    fps={timeline.fps}
    durationInFrames={Math.round(timeline.durationSec * timeline.fps)}
  />
  </>
);
