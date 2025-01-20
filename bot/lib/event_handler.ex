defmodule EventHandler do
  alias ElixirSense.Log
  use GenServer
  require Logger

  def start_link({event_data}) do
    GenServer.start_link(__MODULE__, {event_data})
  end

  def init({event_data}) do
    handle_event(event_data)
    {:ok, {event_data}}
  end

  defp handle_event(%{t: "MESSAGE_CREATE", d: message}) do
    Logger.info("processing message create: #{message.id}")

    Logger.info("message: #{inspect(message)}")
    Logger.info("message.author: #{inspect(message.author)}")
    # Use get_in with default value false if path doesn't exist
    is_bot = get_in(message, [:author, :bot]) || false
    Logger.info("message.author.bot: #{inspect(is_bot)}")
    Logger.info("message.type: #{inspect(message.type)}")

    if message.author == nil or
       get_in(message, [:author, :bot]) || false or
       message.type != 0 do
        Process.exit(self(), :normal)
    end

    Logger.info("calling process_proxy")

    Logic.process_proxy(message)
  end

  defp handle_event(%{t: "MESSAGE_UPDATE", d:  message}) do
    {:ok, channel} = Cache.get_channel(message.guild_id, message.channel_id)
    if message.id != channel.last_message_id do
      Process.exit(self(), :normal)
    end

    Logger.info("processing message update: #{message.id}")
    Logic.process_proxy(message)
  end

  defp handle_event(event) do
    Logger.info("Unhandled event type: #{inspect(event)}")
    Process.exit(self(), :normal)
  end
end
