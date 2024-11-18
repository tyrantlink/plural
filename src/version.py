from subprocess import PIPE, run


START_COMMIT = '2f6d679338fe64940e7d6e606e4424bce9d2d125'
VERSION = '2.0.0'
LAST_TEN_COMMITS: list[str] = []


def _read_commits() -> dict[str, str]:
    global LAST_TEN_COMMITS

    process = run(
        'git log --pretty=oneline',
        shell=True, stdout=PIPE, text=True
    )

    commits = {
        commit.split(' ', 1)[0]: commit.split(' ', 1)[1]
        for commit in reversed(process.stdout.splitlines())
    }

    LAST_TEN_COMMITS = [
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

    for commit in commits.copy():
        del commits[commit]

        if commit == START_COMMIT:
            break

    else:
        raise ValueError('start commit not found')

    return commits


def calculate_version(
    commits: dict[str, str]
) -> list[int]:
    version = list(map(int, VERSION.split('.')))

    for message in commits.values():
        match message.strip().lower()[:6]:
            case 'major;':
                version = [version[0]+1, 0, 0]
            case 'minor;':
                version = [version[0], version[1]+1, 0]
            case 'patch;' | _:
                version[2] += 1

    return version


def load_semantic_version() -> None:
    global VERSION
    commits = _read_commits()
    filtered_commits = _find_start_commit(commits)
    version = calculate_version(filtered_commits)

    VERSION = '.'.join(map(str, version))
