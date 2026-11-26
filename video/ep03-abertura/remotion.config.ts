import { Config } from "@remotion/cli/config";

// Entrega para Reels: 1080 × 1920, 30 fps, H.264 yuv420p, AAC.
// Quadros em PNG para não amaciar as bordas das letras antes da compressão.
Config.setVideoImageFormat("png");
Config.setCodec("h264");
Config.setCrf(16);
Config.setX264Preset("slow");
Config.setPixelFormat("yuv420p");
Config.setAudioCodec("aac");
Config.setAudioBitrate("320k");
Config.setOverwriteOutput(true);
