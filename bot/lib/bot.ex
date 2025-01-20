defmodule Bot do
  use Application
  require Logger

  def start(_type, _args) do
    Logger.info("Starting bot...")

    load_config()

    children = [
      EventSupervisor,
      RedisSubscriber,
      {Redix, {Application.get_env(:bot, :redis_url), name: :redix}}
    ]

    opts = [strategy: :one_for_one, name: YourApp.Supervisor]
    Supervisor.start_link(children, opts)
  end

  defp load_config do
    Application.put_env(:bot, :bot_token, System.fetch_env!("BOT_TOKEN"))
    Application.put_env(:bot, :bot_token, System.fetch_env!("DISCORD_URL"))
    Application.put_env(:bot, :redis_url, System.fetch_env!("REDIS_URL"))
  end
end
