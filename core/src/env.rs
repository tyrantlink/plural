use std::{env::var, sync::OnceLock};


static ENV: OnceLock<Env> = OnceLock::new();

#[derive(Debug)]
pub struct Env {
    pub bot_token: String,
    pub redis_url: String,
    pub mongo_url: String,
    pub domain: String,
    pub max_avatar_size: u32,
    pub dev: bool,
    pub internal_master_token: String,
    pub admins: Vec<u64>,
    pub patreon_secret: String,
    pub info_bot_token: String,
    // ? properties
    pub avatar_url: String
}

impl Default for Env {
    fn default() -> Self {
        let dev = cfg!(debug_assertions);

        let domain = var("DOMAIN").unwrap_or("example.com".to_string());

        Self {
            bot_token: var("BOT_TOKEN").expect("BOT_TOKEN is not set"),
            redis_url: var("REDIS_URL").expect("REDIS_URL is not set"),
            mongo_url: var("MONGO_URL").expect("MONGO_URL is not set"),
            domain: domain.clone(),
            max_avatar_size: var("MAX_AVATAR_SIZE")
                .unwrap_or("4194304".to_string())
                .parse()
                .expect("MAX_AVATAR_SIZE is not a valid number"),
            dev,
            internal_master_token: var("INTERNAL_MASTER_TOKEN")
                .expect("INTERNAL_MASTER_TOKEN is not set"),
            admins: var("ADMINS")
                .unwrap_or("".to_string())
                .split(',')
                .filter_map(|s| s.parse::<u64>().ok())
                .collect(),
            patreon_secret: var("PATREON_SECRET").unwrap_or("".to_string()),
            info_bot_token: var("INFO_BOT_TOKEN").unwrap_or("".to_string()),
            // ? properties
            avatar_url: format!(
                "https://cdn{}.{}/images/{{parent_id}}/{{hash}}.webp",
                if dev { "dev" } else { "" },
                domain
            )
        }
    }
}

impl Env {
    pub fn new() -> Self {
        Self::default()
    }
}

pub fn env() -> &'static Env {
    ENV.get_or_init(Env::new)
}
