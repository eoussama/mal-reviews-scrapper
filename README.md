# MAL Reviews Scrapper

[![Archived MAL Reviews](https://github.com/EOussama/mal-reviews-scrapper/actions/workflows/action.yml/badge.svg?branch=main)](https://github.com/EOussama/mal-reviews-scrapper/actions/workflows/action.yml)

Created for my personal archiving needs.

## Requirements

- [uv](https://docs.astral.sh/uv/)

## Usage

```sh
uv run src/scrape.py [mal_user_name]
```

or

```sh
./scripts/run.sh [mal_user_name]
```

The username defaults to `Eoussama`. Reviews are saved in `out/<mal_user_name>/`, both as one `reviews.json` and as one file per review in `reviews/`.

To build the preview page in `build/`, comparing the scrapped reviews against the latest snapshot in `cache/`:

```sh
./scripts/deploy.sh [mal_user_name]
```

To scrape (if needed), build and serve the preview page on <http://localhost:8000/>:

```sh
./scripts/preview.sh [mal_user_name]
```

`public/index.html` is only a template; opening it directly won't find its `assets/`.

To save a new cache snapshot after scrapping, pass `--snapshot`:

```sh
./scripts/run.sh Eoussama --snapshot
```

The GitHub workflow runs on every push to `main`, weekly on Mondays, and on manual dispatch, then publishes the preview page to the `gh-pages` branch.
