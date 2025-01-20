#!lua name=publish
---@diagnostic disable: undefined-global

-- todo: try to deduplicate a lot of the update functions

local PUBLISHED_EVENTS = {
    'MESSAGE_CREATE',
    'MESSAGE_UPDATE',
    'MESSAGE_REACTION_ADD',
    'WEBHOOKS_UPDATE'
}

local KNOWN_UNSUPPORTED_EVENTS = {

}

local Response = {
    PUBLISHED = 0,
    DUPLICATE = 1,
    CACHED = 2,
    UNSUPPORTED = 3
}


---@param table table
---@param value any
---@return boolean
local function contains(table, value)
    for _, v in pairs(table) do
        if v == value then
            return true
        end
    end
    return false
end

---@param table1 table
---@param table2 table
---@return table
local function merge(table1, table2)
    for k, v in pairs(table2) do
        if type(v) == "table" and type(table1[k]) == "table" then
            merge(table1[k], v)
        else
            table1[k] = v
        end
    end
    return table1
end

---@param data table
---@return table
local function stripped(data)
    data['content'] = nil -- strip content from the cache
    data['attachments'] = nil -- strip attachments from the cache
    return data
end

---@param pattern string
local function bulk_delete(pattern)
    local cursor = '0'
    repeat
        local result = redis.call('SCAN', cursor, 'MATCH', pattern, 'COUNT', 1000)
        cursor = result[1]
        local keys = result[2]

        for _, key in ipairs(keys) do
            redis.call('DEL', key)
        end
    until cursor == '0'
end

---@param data table
---@param meta table | nil
local function cache_model(data, meta)
    return '{' ..
        '"data":' .. cjson.encode(data) .. ',' ..
        '"meta":' .. cjson.encode(meta or {}) .. ',' ..
        '"deleted":0,' ..
        '"error":0' ..
        '}'
end

---@param data table
local function user_update(data)
    local key = 'discord:user:' .. data['id']

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.SET',
            key, 'data', cjson.encode(merge(cjson.decode(cache), data))
        )
    else
        redis.call(
            'JSON.SET',
            key, '$', cache_model(data)
        )
    end

    redis.call('EXPIRE', key, 86400)
end

---@param data table
local function member_update(data)
    local user_id = nil
    if data['user'] then
        user_id = data['user']['id']
        user_update(data['user'])
    else
        user_id = data['user_id']
    end

    data['user'] = nil

    local key = 'discord:member:' .. data['guild_id'] .. ':' .. user_id

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.SET',
            key, 'data', cjson.encode(merge(cjson.decode(cache), data))
        )
    else
        redis.call(
            'JSON.SET',
            key, '$', cache_model(data)
        )
    end

    redis.call('EXPIRE', key, 86400)
end

---@param data table
local function message_create_update(data)
    local key = 'discord:message:' .. data['id']

    local author_id = data['author']['id']

    user_update(data['author'])

    if data['member'] then
        member_update(merge(data['member'],
            {guild_id = data['guild_id'],
            user_id = author_id}
        ))
    end

    data['author'] = nil
    data['member'] = nil

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call('JSON.SET', key, 'data',
            cjson.encode(stripped(merge(cjson.decode(cache), data))))
    else
        redis.call(
            'JSON.SET',
            key, '$', cache_model(
                stripped(data),
                {author_id = author_id}
            )
        )
    end

    redis.call('EXPIRE', key, 3600)
end

---@param data table
local function message_delete(data)
    local key = 'discord:message:' .. data['id']

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.MSET',
            key, 'deleted', 1,
            key, 'data', cjson.encode(data)
        )
    end

    redis.call('EXPIRE', key, 86400)
end

---@param data table
local function role_create_update(data)
    local key = 'discord:role:' .. data['guild_id'] .. ':' .. data['role']['id']

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.SET',
            key, 'data', cjson.encode(merge(cjson.decode(cache), data['role']))
        )
    else
        redis.call(
            'JSON.SET',
            key, '$', cache_model(data['role'])
        )
    end

    redis.call('EXPIRE', key, 86400)

    local guild_key = 'discord:guild:' .. data['guild_id']

    local guild_meta = redis.call('JSON.GET', guild_key, 'meta')

    if not guild_meta then
        return
    end

    local meta = cjson.decode(guild_meta)

    if not contains(meta['roles'], data['role']['id']) then
        table.insert(meta['roles'], data['role']['id'])

        redis.call(
            'JSON.SET',
            guild_key, 'meta', cjson.encode(meta)
        )
    end
end

---@param data table
local function role_delete(data)
    local key = 'discord:role:' .. data['guild_id'] .. ':' .. data['role_id']

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.MSET',
            key, 'deleted', 1,
            key, 'data', cjson.encode(data)
        )
    end
end

---@param guild_id string
---@param emoji table
local function _insert_single_emoji(guild_id, emoji)
    local key = 'discord:emojis:' .. guild_id .. ':' .. emoji['id']

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.SET',
            key, 'data', cjson.encode(merge(cjson.decode(cache), emoji))
        )
    else
        redis.call(
            'JSON.SET',
            key, '$', cache_model(emoji)
        )
    end

    redis.call('EXPIRE', key, 86400)
end

---@param data table
local function guild_emojis_update(data)
    for _, emoji in ipairs(data['emojis']) do
        _insert_single_emoji(data['guild_id'], emoji)
    end
end


---@param data table
local function channel_create_update(data)
    local key = nil
    if data['guild_id'] then
        key = 'discord:channel:' .. data['guild_id'] .. ':' .. data['id']
    else
        key = 'discord:channel:' .. data['id']
    end

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.SET',
            key, 'data', cjson.encode(merge(cjson.decode(cache), data))
        )
    else
        redis.call(
            'JSON.SET',
            key, '$', cache_model(data)
        )
    end

    redis.call('EXPIRE', key, 86400)
end

---@param channel string
---@param guild string|nil
---@param message_id string
local function update_last_channel_message(channel, guild, message_id)
    if not guild then
        return
    end

    redis.call(
        'JSON.SET',
        'discord:channel:' .. guild .. ':' .. channel,
        'data.last_message_id',
        '"' .. message_id .. '"',
        'XX'
    )
end

---@param data table
local function channel_delete(data)
    local key = nil
    if data['guild_id'] then
        key = 'discord:channel:' .. data['guild_id'] .. ':' .. data['id']
    else
        key = 'discord:channel:' .. data['id']
    end

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.MSET',
            key, 'deleted', 1,
            key, 'data', cjson.encode(data)
        )
    end
end


---@param data table
local function guild_create_update(data)
    local roles = {}
    if data['roles'] then
        for _, role in ipairs(data['roles']) do
            table.insert(roles, role['id'])
            role_create_update({
                guild_id = data['id'],
                role = role
            })
        end
        data['roles'] = nil
    end

    if data['members'] then
        for _, member in ipairs(data['members']) do
            member_update(merge(
                member,
                {guild_id = data['id']}
            ))
        end
        data['members'] = nil
    end

    if data['channels'] then
        for _, channel in ipairs(data['channels']) do
            channel_create_update(merge(
                channel,
                {guild_id = data['id']}
            ))
        end
        data['channels'] = nil
    end

    if data['emojis'] then
        guild_emojis_update({
            guild_id = data['id'],
            emojis = data['emojis']
        })
        data['emojis'] = nil
    end

    local key = 'discord:guild:' .. data['id']

    local cache = redis.call('JSON.GET', key, 'data')

    if cache then
        redis.call(
            'JSON.SET',
            key, 'data', cjson.encode(merge(cjson.decode(cache), data))
        )
    else
        redis.call(
            'JSON.SET',
            key, '$', cache_model(data, {roles = roles})
        )
    end

    redis.call('EXPIRE', key, 86400)
end

---@param data table
local function guild_delete(data)
    if data['unavailable'] ~= false then
        return
    end

    local guild_id = data['id']

    redis.call('DEL', 'discord:guild:' .. guild_id)
    bulk_delete('discord:channel:' .. guild_id .. ':*')
    bulk_delete('discord:role:' .. guild_id .. ':*')
    bulk_delete('discord:member:' .. guild_id .. ':*')
    bulk_delete('discord:emojis:' .. guild_id .. ':*')
end

---@param data table
local function message_reaction_add(data)
    --? we don't care about the reaction, just extract the user/ member
    if data['member'] then
        member_update(merge(data['member'],
            {guild_id = data['guild_id'],
            user_id = data['user_id']}
        ))
    end
end

---@param value string
---@return integer
local function cache(value)
    ---@type table
    local event = cjson.decode(value)

    local name = event['t']

    if name == 'MESSAGE_CREATE' then
        message_create_update(event['d'])
        update_last_channel_message(event['d']['channel_id'], event['d']['guild_id'], event['d']['id'])
    elseif name == 'MESSAGE_UPDATE' then
        message_create_update(event['d'])
    elseif name == 'MESSAGE_DELETE' then
        message_delete(event['d'])
    elseif name == 'GUILD_CREATE' then
        guild_create_update(event['d'])
    elseif name == 'GUILD_UPDATE' then
        guild_create_update(event['d'])
    elseif name == 'GUILD_DELETE' then
        guild_delete(event['d'])
    elseif name == 'GUILD_ROLE_CREATE' then
        role_create_update(event['d'])
    elseif name == 'GUILD_ROLE_UPDATE' then
        role_create_update(event['d'])
    elseif name == 'GUILD_ROLE_DELETE' then
        role_delete(event['d'])
    elseif name == 'GUILD_EMOJIS_UPDATE' then
        guild_emojis_update(event['d'])
    elseif name == 'CHANNEL_CREATE' then
        channel_create_update(event['d'])
    elseif name == 'CHANNEL_UPDATE' then
        channel_create_update(event['d'])
    elseif name == 'CHANNEL_DELETE' then
        channel_delete(event['d'])
    elseif name == 'GUILD_MEMBER_UPDATE' then
        member_update(event['d'])
    elseif name == 'MESSAGE_REACTION_ADD' then
        message_reaction_add(event['d'])
    elseif name == 'WEBHOOKS_UPDATE' then
        return Response.PUBLISHED --? this is handled by the downstream bot
    elseif contains(KNOWN_UNSUPPORTED_EVENTS, name) then
        return Response.CACHED
    else
        return Response.UNSUPPORTED
    end

    if contains(PUBLISHED_EVENTS, name) then
        return Response.PUBLISHED
    else
        return Response.CACHED
    end
end

redis.register_function(
    'publish',
    function(keys, args)
        --? just a note that for some reason, json is more memory efficient than just a string
        --? using only 88 bytes vs 96, BUT you can't set expiry in the same call, so i'm sticking with set
        if not redis.call(
            'SET',
            'event:' .. redis.sha1hex(args[1]),
            '1', --? 1 takes less space than an empty string, for some reason, i dunno redis has the stupid
            'NX',
            'EX',
            60
        ) then
            return Response.DUPLICATE
        end

        local cached = cache(args[1])

        if cached == Response.PUBLISHED then
            redis.call(
                'PUBLISH',
                keys[1],
                args[1])
        elseif cached == Response.UNSUPPORTED then
            redis.call(
                'PUBLISH',
                'unsupported_events',
                args[1] --cjson.decode(args[1])['t']
            )
        end

        return cached
    end
)

redis.register_function(
    'cache',
    function(keys, args)
        cache(args[1])
    end
)