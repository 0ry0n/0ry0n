"""Update the profile's statistics from public GitHub repositories only."""

import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- STATS:START -->'
END = '<!-- STATS:END -->'


def public_repositories(owner):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': '0ry0n-profile'}
    if token := os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = f'Bearer {token}'
    repositories = []
    page = 1
    while True:
        url = f'https://api.github.com/users/{quote(owner, safe="")}/repos?type=owner&per_page=100&page={page}'
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('Expected a list of repositories from GitHub')
        repositories.extend(r for r in batch if not r['private'] and r['owner']['login'].lower() == owner.lower())
        if len(batch) < 100:
            return repositories
        page += 1


def render_statistics(repositories, date):
    originals = [r for r in repositories if not r['fork']]
    stars = sum(r['stargazers_count'] for r in originals)
    forks = sum(r['forks_count'] for r in originals)
    return (
        '| Stars on original repos | Forks of original repos | Public repositories |\n'
        '| :---: | :---: | :---: |\n'
        f'| **{stars:,}** | **{forks:,}** | **{len(repositories):,}** |\n\n'
        f'<sub>Public data · checked {date}. Stars and forks exclude forked repositories.</sub>'
    )


def replace_statistics(readme, content):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError('README must contain exactly one pair of statistics markers')
    before, rest = readme.split(START)
    if END not in rest:
        raise ValueError('Statistics markers are out of order')
    _, after = rest.split(END)
    return f'{before}{START}\n{content}\n{END}{after}'


def main():
    owner = os.environ.get('PROFILE_OWNER', '0ry0n')
    repositories = public_repositories(owner)
    date = datetime.now(ZoneInfo('Europe/Rome')).date().isoformat()
    path = ROOT / 'README.md'
    updated = replace_statistics(path.read_text(encoding='utf-8'), render_statistics(repositories, date))
    path.write_text(updated, encoding='utf-8')
    print(f'Updated public statistics for {owner}: {len(repositories)} repositories')


if __name__ == '__main__':
    main()
