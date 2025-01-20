defmodule RedisSubscriber do
  use GenServer
  require Logger

  def start_link(_opts) do
    GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  end

  def init(_state) do
    Logger.info("Initializing Redis subscriber...")
    redis_url = Application.get_env(:bot, :redis_url)

    {:ok, redis_conn} = Redix.start_link(redis_url)
    {:ok, pubsub_conn} = Redix.PubSub.start_link(redis_url)

    Logger.info("Connected to Redis at #{redis_url}")

    Redix.PubSub.subscribe(pubsub_conn, "discord_events", self())
    Logger.info("Subscribed to discord_events channel, waiting for events...")

    {:ok, %{redis: redis_conn, pubsub: pubsub_conn}}
  end

  def handle_call(:get_redis_conn, _from, %{redis: redis_conn} = state) do
    Logger.info("returning redis_conn")
    {:reply, redis_conn, state}
  end

  def handle_call(msg, _from, state) do
    Logger.error("Unknown call: #{inspect(msg)}")
    {:reply, {:error, :unknown_call}, state}
  end

  def handle_info({:redix_pubsub, _pid, _ref, :subscribed, %{channel: channel}}, state) do
    Logger.info("Successfully subscribed to channel: #{channel}")
    {:noreply, state}
  end

  def handle_info({:redix_pubsub, _pid, _ref, :unsubscribed, %{channel: channel}}, state) do
    Logger.info("Unsubscribed from channel: #{channel}")
    {:noreply, state}
  end

  def handle_info({:redix_pubsub, _pid, _ref, :message, %{channel: _channel, payload: payload}}, state) do
    with {:ok, event_data} <- Jason.decode(payload, keys: :atoms) do
      EventSupervisor.start_event_handler({event_data})
    end

    {:noreply, state}
  end

  def handle_info({:redix_pubsub, _pid, _ref, :disconnected, %{error: error}}, state) do
    Logger.error("Disconnected from Redis PubSub: #{inspect(error)}")
    {:noreply, state}
  end
end
