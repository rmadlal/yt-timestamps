import argparse
import requests
from datetime import timedelta

DISCOGS_SEARCH = 'https://api.discogs.com/database/search'
TOKEN = 'hAzLxILnlVAkXByQddbJcvsaYnmjytIXnuxzfYHm'


def str_to_timedelta(duration: str):
    time_parts = list(map(int, duration.split(':')))
    return timedelta(minutes=time_parts[0], seconds=time_parts[1])


def timedelta_to_str(td: timedelta):
    s = str(td)
    if s.startswith('0:'):
        return ':'.join(s.split(':')[1:])
    return s


def get_or_empty(url: str):
    with requests.get(url) as response:
        return response.json() if response.ok else {}


def get_tracklist_data(query):
    data = get_or_empty(f'{DISCOGS_SEARCH}?q={query}&token={TOKEN}')
    if not data['results']:
        return []
    data = get_or_empty(data['results'][0]['resource_url'])
    tracklist = [track for track in data['tracklist'] if track['type_'] == 'track']
    return tuple(zip(*((track['position'], str_to_timedelta(track['duration']), track['title'])
                       for track in tracklist)))


def calculate_timestamps(durations):
    timestamps = [timedelta()]
    for duration in durations[:-1]:
        timestamps.append(timestamps[-1] + duration)
    return timestamps


def organize_lines(positions, timestamps, titles, prefix, separator, numbered):
    return [(f'{prefix} ' if prefix else '') +
            (f'{position}. ' if numbered else '') +
            (f'{timestamp} {separator} {title}' if separator else f'{timestamp} {title}')
            for position, timestamp, title in zip(positions, map(timedelta_to_str, timestamps), titles)]


def main():
    parser = argparse.ArgumentParser(description='Generate tracklist timestamps for YouTube video description')
    parser.add_argument('title', nargs='+', help='the (artist name and) album title')
    parser.add_argument('-n', '--numbered', action='store_true', help='display track numbers')
    parser.add_argument('-p', '--prefix', help='beginning of line')
    parser.add_argument('-s', '--separator', help='separator between timestamp and title')
    args = parser.parse_args()

    query = ' '.join(args.title)
    positions, durations, titles = get_tracklist_data(query)
    timestamps = calculate_timestamps(durations)
    lines = organize_lines(positions, timestamps, titles, args.prefix, args.separator, args.numbered)

    print('\n'.join(lines))


if __name__ == '__main__':
    main()
