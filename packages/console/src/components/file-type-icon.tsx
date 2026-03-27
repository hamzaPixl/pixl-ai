import type { ComponentType } from "react";
import {
  SiPython,
  SiTypescript,
  SiJavascript,
  SiHtml5,
  SiCss,
  SiJson,
  SiMarkdown,
  SiYaml,
  SiDocker,
  SiGo,
  SiRust,
  SiSwift,
  SiKotlin,
  SiRuby,
  SiGnubash,
  SiToml,
  SiSvg,
} from "react-icons/si";
import {
  VscFile,
  VscFileCode,
  VscFilePdf,
  VscFileMedia,
  VscDatabase,
} from "react-icons/vsc";

type IconComponent = ComponentType<{
  className?: string;
  style?: React.CSSProperties;
}>;

const EXT_ICON_MAP: Record<string, { icon: IconComponent; color: string }> = {
  ".py": { icon: SiPython, color: "#3572a5" },
  ".ts": { icon: SiTypescript, color: "#3178c6" },
  ".tsx": { icon: SiTypescript, color: "#3178c6" },
  ".js": { icon: SiJavascript, color: "#f1e05a" },
  ".jsx": { icon: SiJavascript, color: "#f1e05a" },
  ".json": { icon: SiJson, color: "#292929" },
  ".md": { icon: SiMarkdown, color: "#083fa1" },
  ".mdx": { icon: SiMarkdown, color: "#083fa1" },
  ".html": { icon: SiHtml5, color: "#e34c26" },
  ".css": { icon: SiCss, color: "#563d7c" },
  ".scss": { icon: SiCss, color: "#c6538c" },
  ".yaml": { icon: SiYaml, color: "#cb171e" },
  ".yml": { icon: SiYaml, color: "#cb171e" },
  ".toml": { icon: SiToml, color: "#9c4221" },
  ".sh": { icon: SiGnubash, color: "#89e051" },
  ".bash": { icon: SiGnubash, color: "#89e051" },
  ".go": { icon: SiGo, color: "#00add8" },
  ".rs": { icon: SiRust, color: "#dea584" },
  ".rb": { icon: SiRuby, color: "#701516" },
  ".swift": { icon: SiSwift, color: "#f05138" },
  ".kt": { icon: SiKotlin, color: "#a97bff" },
  ".dockerfile": { icon: SiDocker, color: "#384d54" },
  ".svg": { icon: SiSvg, color: "#ff9900" },
  ".sql": { icon: VscDatabase, color: "#e38c00" },
  ".pdf": { icon: VscFilePdf, color: "#ec4444" },
  ".png": { icon: VscFileMedia, color: "#a8b9cc" },
  ".jpg": { icon: VscFileMedia, color: "#a8b9cc" },
  ".jpeg": { icon: VscFileMedia, color: "#a8b9cc" },
  ".gif": { icon: VscFileMedia, color: "#a8b9cc" },
  ".webp": { icon: VscFileMedia, color: "#a8b9cc" },
  ".java": { icon: VscFileCode, color: "#b07219" },
};

const FALLBACK = { icon: VscFile, color: "#6b7280" };

export function FileTypeIcon({
  ext,
  className = "h-4 w-4",
}: {
  ext: string;
  className?: string;
}) {
  const { icon: Icon, color } = EXT_ICON_MAP[ext] ?? FALLBACK;
  return <Icon className={className} style={{ color }} />;
}

/** Get the brand color for an extension (used in charts) */
export function getExtColor(ext: string): string {
  return (EXT_ICON_MAP[ext] ?? FALLBACK).color;
}
