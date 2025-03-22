# Using Multiple Accounts

With /plu/ral, you can share your data across multiple discord accounts.

The target account must have no data.

If the target account has data, you must delete it with the `/delete_all_data` command.

### Sharing
- Use the `/account share` command and select the user you want to share with.
- Use the `/account accept` command on the other account, and select the first account.

This synchronizes all data between the two accounts; the accounts are internally treated as one account, with one exception: group shares are per discord account and will not be inherited by the other account.
