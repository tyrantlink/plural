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
        local result = server.call('SCAN', cursor, 'MATCH', pattern, 'COUNT', 1000)
        cursor = result[1]
        local keys = result[2]

        for _, key in ipairs(keys) do
            server.call('DEL', key)
        end
    until cursor == '0'
end

---@param data table
local function user_update(data)
    local key = 'discord:user:' .. data['id']

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call('HSET', key, 'data', cmsgpack.pack(merge(cmsgpack.unpack(cache), data)))
    else
        server.call(
            'HSET',
            key,
            'data', cmsgpack.pack(data),
            'meta', '',
            'deleted', 0,
            'error', 0
        )
    end

    server.call(
        'EXPIRE',
        key,
        86400
    )
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

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call('HSET', key, 'data', cmsgpack.pack(merge(cmsgpack.unpack(cache), data)))
    else
        server.call(
            'HSET',
            key,
            'data', cmsgpack.pack(data),
            'meta', '',
            'deleted', 0,
            'error', 0
        )
    end

    server.call(
        'EXPIRE',
        key,
        86400
    )
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

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call('HSET', key, 'data',
            cmsgpack.pack(stripped(merge(cmsgpack.unpack(cache), data))))
    else
        server.call(
            'HSET',
            key,
            'data', cmsgpack.pack(stripped(data)),
            'meta', cmsgpack.pack({author_id = author_id}),
            'deleted', 0,
            'error', 0
        )
    end

    server.call(
        'EXPIRE',
        key,
        3600
    )
end

---@param data table
local function message_delete(data)
    local key = 'discord:message:' .. data['id']

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call(
            'HSET',
            key,
            'deleted', 1,
            'data', cmsgpack.pack(data)
        )
    end

    server.call(
        'EXPIRE',
        key,
        86400
    )
end

---@param data table
local function role_create_update(data)
    local key = 'discord:role:' .. data['guild_id'] .. ':' .. data['role']['id']

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call('HSET', key, 'data', cmsgpack.pack(merge(cmsgpack.unpack(cache), data['role'])))
    else
        server.call(
            'HSET',
            key,
            'data', cmsgpack.pack(data['role']),
            'meta', '',
            'deleted', 0,
            'error', 0
        )
    end

    server.call(
        'EXPIRE',
        key,
        86400
    )

    local guild_key = 'discord:guild:' .. data['guild_id']

    local guild_meta = server.call('HGET', guild_key, 'meta')

    if not guild_meta then
        return
    end

    local meta = cmsgpack.unpack(guild_meta)

    if not contains(meta['roles'], data['role']['id']) then
        table.insert(meta['roles'], data['role']['id'])

        server.call(
            'HSET',
            guild_key,
            'meta', cmsgpack.pack(meta)
        )
    end
end

---@param data table
local function role_delete(data)
    local key = 'discord:role:' .. data['guild_id'] .. ':' .. data['role_id']

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call(
            'HSET',
            key,
            'deleted', 1,
            'data', cmsgpack.pack(data)
        )
    end
end

---@param guild_id string
---@param emoji table
local function _insert_single_emoji(guild_id, emoji)
    local key = 'discord:emojis:' .. guild_id .. ':' .. emoji['id']

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call('HSET', key, 'data', cmsgpack.pack(merge(cmsgpack.unpack(cache), emoji)))
    else
        server.call(
            'HSET',
            key,
            'data', cmsgpack.pack(emoji),
            'meta', '',
            'deleted', 0,
            'error', 0
        )
    end

    server.call(
        'EXPIRE',
        key,
        86400
    )
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

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call('HSET', key, 'data', cmsgpack.pack(merge(cmsgpack.unpack(cache), data)))
    else
        server.call(
            'HSET',
            key,
            'data', cmsgpack.pack(data),
            'meta', '',
            'deleted', 0,
            'error', 0
        )
    end

    server.call(
        'EXPIRE',
        key,
        86400
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

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call(
            'HSET',
            key,
            'deleted', 1,
            'data', cmsgpack.pack(data)
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

    local cache = server.call('HGET', key, 'data')

    if cache then
        server.call('HSET', key, 'data', cmsgpack.pack(merge(cmsgpack.unpack(cache), data)))
    else
        server.call(
            'HSET',
            key,
            'data', cmsgpack.pack(data),
            'meta', cmsgpack.pack({roles = roles}),
            'deleted', 0,
            'error', 0
        )
    end

    server.call(
        'EXPIRE',
        key,
        86400
    )
end

---@param data table
local function guild_delete(data)
    if data['unavailable'] ~= false then
        return
    end

    local guild_id = data['id']

    server.call('DEL', 'discord:guild:' .. guild_id)
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

server.register_function(
    'publish',
    function(keys, args)
        if not server.call(
            'SET',
            'event:' .. server.sha1hex(args[1]),
            '1', --? 1 takes less space than an empty string, for some reason, i dunno redis has the stupid
            'NX',
            'EX',
            60
        ) then
            return Response.DUPLICATE
        end

        local cached = cache(args[1])

        if cached == Response.PUBLISHED then
            server.call(
                'PUBLISH',
                keys[1],
                args[1])
        elseif cached == Response.UNSUPPORTED then
            server.call(
                'PUBLISH',
                'unsupported_events',
                args[1]--cjson.decode(args[1])['t']
            )
        end

        return cached
    end
)

server.register_function(
    'cache',
    function(keys, args)
        cache(args[1])
    end
)