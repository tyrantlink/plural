#![forbid(unsafe_code)]

use opentelemetry::global;
use plural_core::{
    db::{Group, Member, Usergroup, doc},
    discord::models::Application,
    env,
    init_mongo,
    init_otel,
    shutdown_otel
};


#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ? init mongo before otel so mongo init isn't traced
    // ? we should only be sending metrics, not traces
    init_mongo(false).await?;

    init_otel("metrics")?;

    #[rustfmt::skip]
    let (
        application,
        registered_users,
        groups,
        members,
        userproxies
    ) = tokio::join!(
        Application::fetch(&env().bot_token, true),
        Usergroup::count_documents(doc! {}),
        Group::count_documents(doc! {}),
        Member::count_documents(doc! {}),
        Member::count_documents(doc! {
            "userproxy": { "$ne": null }
        })
    );

    #[rustfmt::skip]
    let (
        application,
        registered_users,
        groups,
        members,
        userproxies
    ) = (
        application?,
        registered_users?,
        groups?,
        members?,
        userproxies?
    );

    let (guilds, users) = (
        application.approximate_guild_count.unwrap_or(0),
        application.approximate_user_install_count.unwrap_or(0)
    );

    let meter = global::meter("metrics");

    for (name, value) in [
        ("guilds", guilds),
        ("users", users),
        ("registered_users", registered_users),
        ("groups", groups),
        ("members", members),
        ("userproxies", userproxies)
    ] {
        meter
            .u64_observable_gauge(name)
            .with_callback(move |observer| {
                observer.observe(value, &[]);
            })
            .build();
    }

    shutdown_otel()
}
