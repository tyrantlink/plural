defmodule Http do
  @discord_api "http://egress-proxy/api/v10"

  def create_message(channel_id, content) do
    headers = [
      {"Authorization", "Bot #{Application.get_env(:bot, :bot_token)}"},
      {"Content-Type", "application/json"}
    ]

    body = Jason.encode!(%{content: content})

    HTTPoison.post!(
      "#{@discord_api}/channels/#{channel_id}/messages",
      body,
      headers
    )
  end

  def replace_message(channel_id, message) do
    headers = [
      {"Authorization", "Bot #{Application.get_env(:bot, :bot_token)}"},
      {"Content-Type", "application/json"}
    ]

    body = Jason.encode!(%{content: message.content})

    [delete_task, post_task] = [
      Task.async(fn ->
        HTTPoison.delete!(
          "#{@discord_api}/channels/#{channel_id}/messages/#{message.id}",
          headers
        )
      end),
      Task.async(fn ->
        HTTPoison.post!(
          "#{@discord_api}/channels/#{channel_id}/messages",
          body,
          headers
        )
      end)
    ]

    [delete_result, post_result] = Task.await_many([delete_task, post_task])

    post_result
  end
end
