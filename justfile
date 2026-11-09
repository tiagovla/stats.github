# Generate all styles with fixture data under /tmp.
preview:
    mkdir -p /tmp/github-stats-preview
    for theme in dark light github-dark github-light tokyodark; do python3 -m github_stats --fixture fixtures --output "/tmp/github-stats-preview/$theme" --theme "$theme"; done
    cp .github/pages/index.html /tmp/github-stats-preview/index.html
    @echo 'Preview: /tmp/github-stats-preview/index.html'

# Generate and open the preview in the default browser.
show: preview
    xdg-open /tmp/github-stats-preview/index.html
