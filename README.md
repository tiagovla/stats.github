# GitHub Stats

[Preview](https://tiagovla.github.io/stats.github/) (example data).

## Dark

![Contribution stats](https://tiagovla.github.io/stats.github/dark/stats.svg)
![Language composition](https://tiagovla.github.io/stats.github/dark/languages.svg)
![Developer activity](https://tiagovla.github.io/stats.github/dark/activity.svg)

## Light

![Contribution stats](https://tiagovla.github.io/stats.github/light/stats.svg)
![Language composition](https://tiagovla.github.io/stats.github/light/languages.svg)
![Developer activity](https://tiagovla.github.io/stats.github/light/activity.svg)

## Use

Copy [workflow.yml](workflow.yml) to `.github/workflows/stats.yml` in your profile repository. Set Pages source to GitHub Actions. The workflow uses the automatic `GITHUB_TOKEN` for public data; optionally add `STATS_TOKEN` for broader access. The workflow runs twice daily and can be started manually.

Choose `dark`, `light`, `github-dark`, `github-light`, or `tokyodark` with `--theme`. The workflow uses `dark` on schedule; select a theme when running it manually.

Embed your generated cards, replacing `USER` and `REPO`:

```md
![Stats](https://USER.github.io/REPO/stats.svg)
![Languages](https://USER.github.io/REPO/languages.svg)
![Activity](https://USER.github.io/REPO/activity.svg)
```

To run locally:

```sh
python -m pip install 'git+https://github.com/tiagovla/stats.github.git'
export GH_TOKEN=your_github_token
python -m github_stats --username USER --output dist --theme dark
```
