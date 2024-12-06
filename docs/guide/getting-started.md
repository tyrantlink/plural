If you're coming from PluralKit or Tupperbox, see the [Importing](https://github.com/tyrantlink/plural/wiki/Importing) page

## Create a member

- use `/member new` and specify a name
  - this name must be unique within a member group, if you don't specify a group, "default" will be used

## Add some proxy tags

- use `/member tags add` and specify a prefix, suffix, or both
  - a tag must have a prefix or a suffix
  - use the `regex` option to have your tags matched with regex, don't use this if you don't know what you're doing
  - use the `case_sensitive` option to make your matches case sensitive, by default, tags are case insensitive
```
/member tags add prefix:/st
/member tags add suffix:--steve
/member tags add prefix:< suffix:>
```

## Set an avatar

- use `/member set avatar` and upload an image
  - the image must be a .jpg, .png, .webp, or .gif and must be under 10mb in size
  - the image will be cropped to 4096x4096, if it's smaller than this, it will be left alone
  - animated gif avatars will only been animated for userproxy accounts (see [Userproxies](https://github.com/tyrantlink/plural/wiki/Userproxies)