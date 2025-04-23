from subprocess import PIPE, run
from os import environ


def _read_commits(service: str) -> dict[str, str]:
    process = run(
        f'git log --pretty=oneline --follow {service}',
        shell=True, stdout=PIPE, text=True, cwd='..'
    )

    return {
        commit.split(' ', 1)[0]: commit.split(' ', 1)[1]
        for commit in reversed(process.stdout.splitlines())
    }


def _find_start_commit(
    commits: dict[str, str]
) -> dict[str, str]:
    start_commit = environ.get('START_COMMIT')

    if not start_commit:
        return commits

    for index, (hash, _message) in enumerate(commits.items()):  # noqa: B007
        if hash == start_commit:
            break
    else:
        raise ValueError('start commit not found')

    return dict(list(commits.items())[index:])


def calculate_version(
    commits: dict[str, str]
) -> list[int]:
    version = [0, 0, 0]

    for message in commits.values():
        match message.strip().lower()[:6]:
            case 'major;':
                version = [version[0]+1, 0, 0]
            case 'minor;':
                version = [version[0], version[1]+1, 0]
            case 'patch;' | _:
                version[2] += 1

    version.insert(
        0, int(environ.get('VERSION_EPOCH', '0'))
    )

    return version


def load_semantic_version(service: str) -> tuple[str, list[str]]:
    commits = _read_commits(service)
    filtered_commits = _find_start_commit(commits)
    version = calculate_version(filtered_commits)

    return (
        '.'.join(map(str, version)) + (
            '-dev'
            if environ.get('DEV', '1') != '0'
            else ''
        ), [
            f'[`{hash[:7]}`](<https://github.com/tyrantlink/plural/commit/{hash}>): {message}'
            for hash, message in
            commits.items()
        ][-10:][::-1]
    )
