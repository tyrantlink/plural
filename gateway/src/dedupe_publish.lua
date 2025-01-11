#!lua name=dedupe_publish
---@diagnostic disable: undefined-global
server.register_function(
    'dedupe_publish',
    function(keys, args)
        if server.call(
            'SET',
            'event_hash:' .. server.sha1hex(args[1]),
            '1', -- 1 takes less space than an empty string, for some reason, i dunno redis has the stupid
            'NX',
            'EX',
            60
        ) then
            return server.call(
                'PUBLISH',
                keys[1],
                args[1]
            )
        end

        return 0
    end
)
