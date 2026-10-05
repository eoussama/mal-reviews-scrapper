import os
import re
import sys
import json
import time
import shutil
import argparse
import unicodedata
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


DEFAULT_USER = 'Eoussama'
USER_AGENT = 'mal-reviews-scrapper (+https://github.com/EOussama/mal-reviews-scrapper)'
REQUEST_TIMEOUT = 30
PAGE_DELAY = 1.5
MAX_RETRIES = 5
RETRY_STATUSES = {429, 500, 502, 503, 504}
NON_RECOMMENDATION_TAGS = {'spoiler', 'preliminary'}


class ScrapeError(Exception):
    pass


def fetch(session, url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as error:
            reason = str(error)
        else:
            if response.status_code == 200:
                return response
            if response.status_code not in RETRY_STATUSES:
                raise ScrapeError(f'GET {url} returned HTTP {response.status_code}.')
            reason = f'HTTP {response.status_code}'

        if attempt < MAX_RETRIES:
            delay = 2 ** attempt
            print(f'GET {url} failed ({reason}), retrying in {delay}s ({attempt}/{MAX_RETRIES}).', file=sys.stderr)
            time.sleep(delay)

    raise ScrapeError(f'GET {url} failed after {MAX_RETRIES} attempts ({reason}).')


def scrape_reviews(user_id):
    base_url = f'https://myanimelist.net/profile/{user_id}/reviews'
    all_reviews = []
    page = 1

    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT

    while True:
        url = base_url if page == 1 else f'{base_url}?p={page}'
        response = fetch(session, url)

        soup = BeautifulSoup(response.content, 'html.parser')
        reviews = soup.find_all('div', class_='review-element')

        if not reviews:
            break

        reviews_scrapped = 0
        for index, review in enumerate(reviews, start=1):
            try:
                review_data = parse_review(review)
            except Exception as error:
                print(f'::warning::Skipped review {index} of page {page}: {error!r}', file=sys.stderr)
                continue

            reviews_scrapped += 1
            all_reviews.append(review_data)

        print(f'Scrapped {reviews_scrapped} of {len(reviews)} review(s) on page {page}.')

        page += 1
        time.sleep(PAGE_DELAY)

    return all_reviews


def parse_review(review):
    review_data = {}

    title = review.find('a', class_='title')
    update_at = review.find('div', class_='update_at')

    review_data['title'] = title.text.strip()
    review_data['url'] = title['href']
    review_data['type'] = get_type(review_data['url'])
    review_data['id'] = get_id(review_data['type'], review_data['url'])
    review_data['date'] = update_at.text.strip()
    review_data['time'] = update_at['title'].strip()
    review_data['datetime'] = get_datetime(review_data['date'], review_data['time'])
    review_data['recommendation'] = get_recommendation(review)
    review_data['rating'] = int(review.find('div', class_='rating').find('span', class_='num').text)
    review_data['content'] = get_content(review.find('div', class_='text'))

    return review_data


def get_recommendation(review):
    for tag in review.find_all('div', class_='tag'):
        if not NON_RECOMMENDATION_TAGS.intersection(tag.get('class', [])):
            return tag.text.strip()

    raise ValueError('No recommendation tag found.')


def get_content(text_element):
    # MAL splits long reviews into a visible part, a "..." marker and a hidden part.
    # Dropping the marker leaves an indented blank line where the two parts meet,
    # which stands for a single space in the rendered page.
    for marker in text_element.select('.js-visible'):
        marker.decompose()

    content = text_element.text.replace('\r\n', '\n')
    content = re.sub(r'\n[ \t]+\n', ' ', content)

    return content.strip()


def get_datetime(date, time_of_day):
    try:
        return datetime.strptime(f'{date} {time_of_day}', '%b %d, %Y %I:%M %p').isoformat()
    except ValueError:
        return None


def save_to_json(reviews, user_id):
    output_dir = f'out/{user_id}'
    reviews_dir = f'{output_dir}/reviews'

    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(reviews_dir)

    for i, review in enumerate(reviews):
        number = len(reviews) - i
        output_name = slugify(f'{number} - {review.get("title")}')

        with open(f'{reviews_dir}/{output_name}.json', 'w', encoding='utf-8') as f:
            json.dump(review, f, indent=4, ensure_ascii=False)

    with open(f'{output_dir}/reviews.json', 'w', encoding='utf-8') as f:
        json.dump(reviews, f, indent=4, ensure_ascii=False)

    print(f'Saved {len(reviews)} review(s) in {output_dir}.')


def save_snapshot(reviews):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S')
    output_file = f'cache/cache-{timestamp}.json'

    os.makedirs('cache', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': timestamp, 'reviews': reviews}, f, indent=4, ensure_ascii=False)

    print(f'Saved cache snapshot in {output_file}.')


def slugify(value, allow_unicode=False):
    value = str(value)

    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')

    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def get_id(review_type, url):
    match = re.search(rf'/{review_type}/(\d+)/', url)

    if not match:
        raise ValueError(f'Could not extract an id from {url}.')

    return int(match.group(1))


def get_type(url):
    parts = [part for part in url.split('/') if part]

    if len(parts) < 4:
        raise ValueError(f'Could not extract a type from {url}.')

    return parts[2]


def main():
    parser = argparse.ArgumentParser(description='Archive the reviews of a MyAnimeList user.')
    parser.add_argument('user_id', nargs='?', default=DEFAULT_USER, help=f'MAL username (default: {DEFAULT_USER})')
    parser.add_argument('--snapshot', action='store_true', help='also save the reviews as a new cache snapshot')
    args = parser.parse_args()

    try:
        reviews = scrape_reviews(args.user_id)
    except ScrapeError as error:
        sys.exit(f'::error::{error}')

    if not reviews:
        sys.exit(f'::error::No reviews were scrapped for {args.user_id}, refusing to overwrite the archive.')

    save_to_json(reviews, args.user_id)

    if args.snapshot:
        save_snapshot(reviews)


if __name__ == '__main__':
    main()
