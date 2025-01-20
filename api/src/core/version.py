from typing import overload, Literal
from subprocess import PIPE, run
# from src.models import project


START_COMMIT = None  # '2f6d679338fe64940e7d6e606e4424bce9d2d125'
BASE_VERSION = '3.0.0' + ('-dev' if True else '')  # ! project.dev_environment


@overload
def _read_commits(last_ten: Literal[True]) -> list[str]:
    ...


@overload
def _read_commits(last_ten: Literal[False] = False) -> dict[str, str]:
    ...


def _read_commits(last_ten: bool = False) -> dict[str, str] | list[str]:
    process = run(
        'git log --pretty=oneline --follow api/',
        shell=True, stdout=PIPE, text=True, cwd='..'
    )

    commits = {
        commit.split(' ', 1)[0]: commit.split(' ', 1)[1]
        for commit in reversed(process.stdout.splitlines())
    }

    if last_ten:
        return [
            f'[`{hash[:7]}`](<https://github.com/tyrantlink/plural/commit/{hash}>): {message}'
            for hash, message in
            commits.items()
        ][-10:][::-1]

    return commits


def _find_start_commit(
    commits: dict[str, str]
) -> dict[str, str]:
    if not START_COMMIT:
        return commits

    for index, commit in enumerate(commits):
        if commit == START_COMMIT:
            break
    else:
        raise ValueError('start commit not found')

    return commits[index:]


def calculate_version(
    commits: dict[str, str]
) -> list[int]:
    version = list(map(int, BASE_VERSION.split('-')[0].split('.')))

    for message in commits.values():
        match message.strip().lower()[:6]:
            case 'major;':
                version = [version[0]+1, 0, 0]
            case 'minor;':
                version = [version[0], version[1]+1, 0]
            case 'patch;' | _:
                version[2] += 1

    return version


def load_semantic_version() -> str:
    commits = _read_commits()
    filtered_commits = _find_start_commit(commits)
    version = calculate_version(filtered_commits)

    return '.'.join(map(str, version)) + \
        ('-dev' if True else '')  # ! project.dev_environment


VERSION = load_semantic_version()
LAST_TEN_COMMITS: list[str] = _read_commits(True)
