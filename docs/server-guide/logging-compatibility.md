## Log Cleaning
/plu/ral has the option to automatically delete delete logs for proxied messages, which can be enabled with the following command:
```text :no-line-numbers
/serverconfig logclean: True
```

### Supported bots
- [Dyno](https://discord.com/application-directory/161660517914509312)
- \*[carl-bot](https://discord.com/application-directory/235148962103951360)
- [ProBot](https://discord.com/application-directory/282859044593598464)
- \*[Catalogger](https://discord.com/application-directory/830819903371739166)

\* These bots have multiple logs in a single message, so some logs may not be deleted, as that could delete logs for other messages.

### Adding support for your logging bot
see the [adding logging support](/third-party-applications/logging-support) page