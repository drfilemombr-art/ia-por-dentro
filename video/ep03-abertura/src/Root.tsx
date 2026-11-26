import React from "react";
import { Composition } from "remotion";
import { Abertura } from "./Abertura";
import timeline from "../data/timeline.json";

export const Root: React.FC = () => (
  <Composition
    id="Abertura"
    component={Abertura}
    width={1080}
    height={1920}
    fps={timeline.fps}
    durationInFrames={Math.round(timeline.durationSec * timeline.fps)}
  />
);
