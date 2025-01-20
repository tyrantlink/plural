defmodule Cache do
  require Logger

  def get_channel(guild_id, channel_id) do
    redis_key = "discord:channel:#{guild_id}:#{channel_id}"

    case Redix.command(:redix, ["FCALL", "unpack_hget", "1", redis_key, "data"]) do
      {:ok, json_string} when is_binary(json_string) ->
        Logger.info("Found cache entry for channel #{channel_id}")
        case Jason.decode(json_string, keys: :atoms) do
          {:ok, data} ->
            Logger.info("Decoded channel data: #{inspect(data)}")
            {:ok, data}
          {:error, error} ->
            Logger.info("Failed to decode channel data: #{inspect(error)}")
            {:error, :invalid_json}
        end
      {:ok, nil} ->
        Logger.info("No cache entry found for channel #{channel_id} in guild #{guild_id}")
        {:error, :not_found}
      {:ok, _} ->
        Logger.info("Unexpected redis response")
        {:error, :not_found}
      {:error, error} ->
        Logger.info("Redis error fetching channel: #{inspect(error)}")
        {:error, :redis_error}
    end
  end
end
