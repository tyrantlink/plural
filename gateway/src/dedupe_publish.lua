#!lua name=dedupe_publish
server.register_function(
    'dedupe_publish',
    function(keys, args)
        if server.call(
            'SET',
            'event_hash:' .. server.sha1hex(args[1]),
            '1',
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
