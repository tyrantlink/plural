use serde::{Deserialize, Serialize};

use crate::discord::{Method, Request};


#[derive(Debug, Serialize, Deserialize)]
pub struct Application {
    pub approximate_guild_count:        Option<u64>,
    pub approximate_user_install_count: Option<u64>
}


impl Application {
    pub async fn fetch(
        token: &str,
        silent: bool
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let mut request = Request::new(
            Method::GET,
            "https://discord.com/api/v10/applications/@me"
        )
        .with_token(token);

        if silent {
            request = request.suppress_tracer();
        }

        request
            .send::<Self>()
            .await?
            .ok_or("Application fetch succeeded but returned no body".into())
    }
}
