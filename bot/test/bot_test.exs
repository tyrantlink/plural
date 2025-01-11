defmodule BotTest do
  use ExUnit.Case
  doctest Bot

  test "greets the world" do
    assert Bot.hello() == :world
  end
end
