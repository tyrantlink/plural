

def subfunc(debug_log: list[str]) -> None:
    debug_log.append("subfunc")


def main(debug_log: list[str]) -> None:
    debug_log.append("main")
    subfunc(debug_log)


if __name__ == "__main__":
    debug_log = []
    main(debug_log)
    print(debug_log)
