use std::env;
use std::process::Command;


fn read_commits(service: &str) -> Vec<(String, String)> {
    let branch = Command::new("git")
        .args(["rev-parse", "--abbrev-ref", "HEAD"])
        .output()
        .expect("Failed to execute git rev-parse command");

    let output = Command::new("git")
        .args([
            "log",
            "--pretty=oneline",
            String::from_utf8(branch.stdout).unwrap().trim(),
            "--follow",
            service
        ])
        .output()
        .expect("Failed to execute git log command");

    String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|line| {
            let (hash, message) = line.split_once(' ').unwrap();
            (hash.to_string(), message.to_string())
        })
        .collect()
}

fn find_start_commit(commits: &[(String, String)]) -> &[(String, String)] {
    let start = &env::var("START_COMMIT")
        .unwrap_or("".to_string());

    if start.is_empty() {
        return commits;
    }

    commits.iter()
        .position(|(hash, _)| hash == start)
        .map(|index| &commits[index..])
        .unwrap_or_else(|| panic!("Start commit {} not found", start))
}

fn calculate_version(commits: &[(String, String)]) -> String {
    let epoch = env::var("VERSION_EPOCH")
        .unwrap_or("0".to_string())
        .parse::<u32>()
        .unwrap_or(0);

    let mut version = vec![0, 0, 0];

    for (_, message) in commits {
        let prefix = message.trim().to_lowercase().chars().take(6).collect::<String>();
        match &prefix[..] {
            s if s.starts_with("major;") => {
                version[0] += 1;
                version[1] = 0;
                version[2] = 0;
            }
            s if s.starts_with("minor;") => {
                version[1] += 1;
                version[2] = 0;
            }
            _ => version[2] += 1,
        }
    }

    let dev_env = env::var("DEV").unwrap_or("1".to_string());

    let dev_suffix = if !(
        dev_env == "false" ||
        dev_env == "0"
    ) {
        "-dev"
    } else {
        ""
    };

    format!("{}.{}.{}.{}{}", epoch, version[0], version[1], version[2], dev_suffix)
}

pub fn get_version(service: &str) -> String {
    calculate_version(
        &find_start_commit(
            &read_commits(service)
        )
    )
}