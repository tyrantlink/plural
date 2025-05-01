pub mod application;
pub mod autoproxy;
pub mod enums;
pub mod group;
pub mod guild;
pub mod member;
pub mod message;
pub mod usergroup;

use std::sync::OnceLock;

use mongodb::{Client, Database};
pub use mongodb::{bson::doc, error::Error as MongoError};
use opentelemetry::{
    global,
    trace::{FutureExt, Tracer}
};

use crate::env::env;

#[rustfmt::skip]
pub use application::Application;
pub use autoproxy::Autoproxy;
pub use group::Group;
pub use guild::Guild;
pub use member::Member;
pub use message::Message;
pub use usergroup::Usergroup;


static MONGO: OnceLock<Database> = OnceLock::new();

pub async fn init_mongo(ping: bool) -> Result<(), Box<dyn std::error::Error>> {
    let tracer = global::tracer("");

    let mongo = tracer
        .in_span("initializing mongo", |cx| {
            async {
                let mongo = Client::with_uri_str(&env().mongo_url)
                    .await?
                    .database("plural");

                // ? ping because simply creating the client doesn't
                // ? actually connect to the database, either that or
                // ? the connection is waaaay faster than i expect
                if ping {
                    mongo.run_command(doc! {"ping": 1}).await?;
                }

                Ok::<Database, MongoError>(mongo)
            }
            .with_context(cx)
        })
        .await?;

    MONGO.set(mongo).expect("Failed to set Mongo client");

    Ok(())
}

pub fn mongo() -> &'static Database {
    MONGO.get().expect("Mongo client not initialized")
}
