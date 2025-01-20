defmodule Logic do
  require Logger

  def process_proxy(message) do
    Logger.info("processing proxy message: #{message.id}")
    Http.create_message(message.channel_id, "pong!")
  end
end
