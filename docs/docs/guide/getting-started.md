# Getting Started

If you're coming from PluralKit or Tupperbox, see the [importing](/guide/importing.md) page information on how to import, and the differences between the bots.

## Create a member

- Use `/member new` and specify a name
  - The combination of name and meta must be unique within a group
  - If you don't specify a group, "default" will be used (or created if it doesn't exist)
  - You can also add an avatar, and proxy tag with this command

See [Members](/guide/members.md) for more information on members, and [Groups](/guide/groups.md) for more information on groups.

```text :no-line-numbers
/member new name:steve
```

## Add some proxy tags

- Use `/member tags add` and specify a prefix, suffix, or both
  - A tag must have a prefix or a suffix
  - Use the `regex` option to have your tags matched with regex, don't use this if you don't know what you're doing
  - Use the `case_sensitive` option to make your matches case sensitive, by default, tags are case insensitive
```text :no-line-numbers
/member tags add prefix:/st
/member tags add suffix:--steve
/member tags add prefix:{ suffix:}
```

See [Proxy Tags](/guide/members.md#proxy-tags) for more information.

## Set an avatar

- Use `/member set avatar` and upload an image
  - The image must be a .jpg, .png, .webp, or .gif and must be under 4mb in size
  - The image will be scaled down to 1024x1024, and converted to webp, if it isn't already.
  - Animated avatars will only be animated for userproxy bots (see [Userproxies](/guide/userproxies.md)).
    - This is a Discord limitation.

## Other Config
Nearly all config is done via the `/config` command, and all config options have built-in descriptions when using the command.

## Proxying in DMs

In order to proxy in DMs you need to attach a userproxy to a member.

See [Userproxies](/guide/userproxies.md) for more information on userproxies and how to create them.