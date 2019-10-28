import argparse
import logging
import requests
from datetime import timedelta
from dataclasses import dataclass, astuple
from functools import partial
from typing import List, Iterable

DISCOGS_SEARCH = 'https://api.discogs.com/database/search'
TOKEN = open('token.txt').read()
DEBUG = 0

MINUTE = 60
HOUR = MINUTE ** 2
OPEN_PARENS = ('(', '[', '{', '<')
CLOSE_PARENS = (')', ']', '}', '>')

logging.basicConfig(format='%(asctime)s\t%(levelname)s\t%(filename)s\t%(lineno)d\t%(message)s', level=logging.DEBUG)


class Timestamp(object):
    """ Wrapper on timedelta, for customized str conversions """

    def __init__(self, *args, **kwargs):
        self._td = timedelta(*args, **kwargs)

    def __add__(self, other: 'Timestamp') -> 'Timestamp':
        ts = Timestamp()
        ts._td = self._td + other._td
        return ts

    def __repr__(self) -> str:
        return f'Timestamp({repr(self._td)})'

    def __str__(self) -> str:
        remainder = int(self._td.total_seconds())
        hours = remainder // HOUR
        remainder %= HOUR
        minutes = remainder // MINUTE
        remainder %= MINUTE
        seconds = remainder

        if hours:
            return f'{hours}:{minutes:02}:{seconds:02}'
        return f'{minutes}:{seconds:02}'

    def format(self, paren: str = None) -> str:
        if paren:
            return f'{paren}{str(self)}{CLOSE_PARENS[OPEN_PARENS.index(paren)]}'
        return str(self)

    @staticmethod
    def from_str(duration: str) -> 'Timestamp':
        parts = duration.split(':')
        if not (duration and 0 < len(parts) <= 3):
            raise ValueError(f'Invalid duration: "{duration}"')
        if len(parts) == 3:
            return Timestamp(hours=int(parts[0]), minutes=int(parts[1]), seconds=int(parts[2]))
        if len(parts) == 2:
            return Timestamp(minutes=int(parts[0]), seconds=int(parts[1]))
        return Timestamp(seconds=int(parts[0]))


@dataclass
class Track:
    position: str
    title: str
    time: Timestamp

    def __iter__(self):
        """ Allows us to unpack (e.g: `position, title, time = track`) """
        yield from astuple(self)


def http_get_json(url: str) -> dict:
    return requests.get(url).json()


def durations_to_timestamps(tracklist: List[Track]) -> None:
    acc_durations = Timestamp()
    for track in tracklist:
        duration = track.time
        track.time = acc_durations
        acc_durations += duration


def get_tracklist_data(query: str) -> List[Track]:
    try:
        if DEBUG > 1:
            import json
            tracklist = json.load(open('sample_tracklist.txt'))
        else:
            results = http_get_json(f'{DISCOGS_SEARCH}?q={query}&type=release&token={TOKEN}')['results']
            if not results:
                logging.error(f'Album not found: "{query}"')
                return []
            release = results[0]
            logging.info(f'Generating tracklist for "{release["title"]}"')
            tracklist = http_get_json(release['resource_url'])['tracklist']

        logging.debug(tracklist)
        tracklist = [Track(track['position'], track['title'], Timestamp.from_str(track['duration']))
                     for track in tracklist if track['type_'] == 'track']
        durations_to_timestamps(tracklist)
        return tracklist

    except (KeyError, ValueError, IndexError, requests.RequestException):
        logging.exception(f'Error getting tracklist for "{query}"')
        return []


def format_lines(tracklist: List[Track], args: argparse.Namespace) -> Iterable[str]:
    prefix = f'{args.prefix} ' if args.prefix else ''
    separator = f' {args.separator} ' if args.separator else ' '
    for position, title, time in tracklist:
        line = prefix
        if args.numbered:
            line += f'{position}. '
        if args.title_first:
            line += f'{title}{separator}{time.format(args.parentheses)}'
        else:
            line += f'{time.format(args.parentheses)}{separator}{title}'
        yield line


def main():
    global DEBUG

    parser = argparse.ArgumentParser(description='Generate tracklist timestamps for YouTube video description')
    parser.add_argument('query', metavar='title', help='the (artist name and) album title')
    parser.add_argument('-n', '--numbered', action='store_true', help='display track numbers')
    parser.add_argument('-tf', '--title-first', action='store_true', help='titles first')
    parser.add_argument('-pr', '--prefix', help='beginning of line')
    parser.add_argument('-s', '--separator', help='separator between title and timestamp')
    parser.add_argument('-pa', '--parentheses', choices=OPEN_PARENS, help='surround timestamps with parentheses')
    parser.add_argument('-o', '--output', type=partial(open, mode='w'), default=None, help='output filename')
    parser.add_argument('-d', '--debug', action='count')
    args = parser.parse_args()

    DEBUG = args.debug or 0
    if not DEBUG:
        logging.disable(logging.DEBUG)
    logging.debug(args)

    tracklist = get_tracklist_data(args.query)
    if not tracklist:
        return

    print('\n'.join(format_lines(tracklist, args)), file=args.output)


if __name__ == '__main__':
    main()
