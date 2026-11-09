"""Color palettes used by the SVG renderers."""

PALETTES = {
    "stats": {
        "dark": {"bg": "#020b16", "panel": "#07182a", "inner": "#00101b", "bezel": "#253b53", "grid": "#07303b", "text": "#a9e2ed", "muted": "#75a9b8", "line": "#0df4f0", "area": "#00c5b2", "preview": "#285b6d", "cell": "#061e29", "levels": ("#06402f", "#07854d", "#00b95c", "#00f56d"), "amber": "#ffc34e", "bezel_hi": "#61758a", "bezel_lo": "#0b192a", "dot_outline": "#d2ffff", "axis": "#5596aa", "highlight": "#9aafc1"},
        "light": {"bg": "#edf5f7", "panel": "#f8fcfd", "inner": "#f3fafb", "bezel": "#b3c9d2", "grid": "#c8dfe4", "text": "#17424b", "muted": "#66858d", "line": "#008e9a", "area": "#00a99f", "preview": "#9dbdc5", "cell": "#e1eeeb", "levels": ("#d6ece2", "#8ad5ad", "#28b976", "#008d57"), "amber": "#be7410", "bezel_hi": "#9aafc1", "bezel_lo": "#b3c9d2", "dot_outline": "#f8fcfd", "axis": "#66858d", "highlight": "#9aafc1"},
        "github-dark": {"bg": "#0d1117", "panel": "#161b22", "inner": "#0d1117", "bezel": "#30363d", "grid": "#21262d", "text": "#e6edf3", "muted": "#8b949e", "line": "#2f81f7", "area": "#1f6feb", "preview": "#388bfd", "cell": "#161b22", "levels": ("#0e4429", "#006d32", "#26a641", "#39d353"), "amber": "#d29922", "bezel_hi": "#484f58", "bezel_lo": "#0d1117", "dot_outline": "#e6edf3", "axis": "#8b949e", "highlight": "#6e7681"},
        "github-light": {"bg": "#ffffff", "panel": "#f6f8fa", "inner": "#ffffff", "bezel": "#d0d7de", "grid": "#d8dee4", "text": "#1f2328", "muted": "#656d76", "line": "#0969da", "area": "#54aeff", "preview": "#80ccff", "cell": "#eaeef2", "levels": ("#aceebb", "#4ac26b", "#2da44e", "#116329"), "amber": "#9a6700", "bezel_hi": "#afb8c1", "bezel_lo": "#d0d7de", "dot_outline": "#ffffff", "axis": "#656d76", "highlight": "#afb8c1"},
        "tokyodark": {"bg": "#11121d", "panel": "#1a1b2a", "inner": "#11121d", "bezel": "#3b4261", "grid": "#282c34", "text": "#a0a8cd", "muted": "#565f89", "line": "#7aa2f7", "area": "#38a89d", "preview": "#4a6f9e", "cell": "#212234", "levels": ("#587738", "#95c561", "#98c379", "#38a89d"), "amber": "#d7a65f", "bezel_hi": "#4a5057", "bezel_lo": "#11121d", "dot_outline": "#c0caf5", "axis": "#565f89", "highlight": "#4a5057"},
    },
    "language": {
        "dark": {"bg": "#020b16", "panel": "#07182a", "track": "#00101b", "border": "#253b53", "grid": "#123142", "text": "#a9e2ed", "muted": "#75a9b8", "unknown": "#8b9aa8"},
        "light": {"bg": "#edf5f7", "panel": "#f8fcfd", "track": "#e1eeeb", "border": "#b3c9d2", "grid": "#d4e5e9", "text": "#17424b", "muted": "#66858d", "unknown": "#66858d"},
        "github-dark": {"bg": "#0d1117", "panel": "#161b22", "track": "#0d1117", "border": "#30363d", "grid": "#30363d", "text": "#e6edf3", "muted": "#8b949e", "unknown": "#8b949e"},
        "github-light": {"bg": "#ffffff", "panel": "#f6f8fa", "track": "#eaeef2", "border": "#d0d7de", "grid": "#d8dee4", "text": "#1f2328", "muted": "#656d76", "unknown": "#656d76"},
        "tokyodark": {"bg": "#11121d", "panel": "#1a1b2a", "track": "#212234", "border": "#3b4261", "grid": "#353945", "text": "#a0a8cd", "muted": "#565f89", "unknown": "#4a5057"},
    },
    "activity": {
        "dark": {"bg": "#020b16", "panel": "#07182a", "border": "#07303b", "text": "#c8e3f1", "muted": "#9bb8c5", "accent": "#00d7e6", "track": "#173841", "rule": "#00a99f", "icon": "#bfdced"},
        "light": {"bg": "#edf5f7", "panel": "#f8fcfd", "border": "#c8dfe4", "text": "#152d40", "muted": "#647e91", "accent": "#087f70", "track": "#dbe6ec", "rule": "#d7e2e9", "icon": "#087f70"},
        "github-dark": {"bg": "#0d1117", "panel": "#161b22", "border": "#30363d", "text": "#e6edf3", "muted": "#8b949e", "accent": "#2f81f7", "track": "#21262d", "rule": "#30363d", "icon": "#79c0ff"},
        "github-light": {"bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de", "text": "#1f2328", "muted": "#656d76", "accent": "#0969da", "track": "#eaeef2", "rule": "#d8dee4", "icon": "#0969da"},
        "tokyodark": {"bg": "#11121d", "panel": "#1a1b2a", "border": "#3b4261", "text": "#a0a8cd", "muted": "#565f89", "accent": "#7aa2f7", "track": "#212234", "rule": "#38a89d", "icon": "#7dcfff"},
    },
}
