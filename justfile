# Generate both themes and a local HTML preview under /tmp.
preview:
    mkdir -p /tmp/github-stats-preview
    python3 -m github_stats --fixture fixtures --output /tmp/github-stats-preview/dark --theme dark
    python3 -m github_stats --fixture fixtures --output /tmp/github-stats-preview/light --theme light
    cp .github/pages/index.html /tmp/github-stats-preview/index.html
    @echo 'Preview: /tmp/github-stats-preview/index.html'

# Generate and open the preview in the default browser.
show: preview
    xdg-open /tmp/github-stats-preview/index.html
