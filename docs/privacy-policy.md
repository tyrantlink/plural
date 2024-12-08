# Privacy Policy
Effective: 13 December 2024

## 1. Data Controller
The Data Controller for /plu/ral is tyrantlink, who can be contacted at support@plural.gg for any privacy-related concerns.

## 2. Legal Basis and Consent
/plu/ral operates on the basis of implicit consent through usage. Data collection only occurs when users actively engage with bot commands. By using the bot's commands, users consent to the data collection necessary for the bot's functionality.

## 3. Perpetual Data Collection
/plu/ral stores all data explicitly provided via interactions, including but not limited to:
- Group data
- Member data
- Config settings

This data is stored indefinitely until explicitly deleted via the `/delete_all_data` command. Long-term storage is necessary to ensure continued functionality even after periods of inactivity.

## 4. Temporary Data Collection
/plu/ral stores some data temporarily for the required functionality of some commands in the following scenarios:

When a message is proxied, a message log object is stored for one (1) day and contains the following data:
| Message Object      |
|---------------------|
| Original Message ID |
| Proxied Message ID  |
| User ID             |
| Channel ID          |
| Proxy Reason        |

When using the userproxy `/proxy` command with the `queue_for_reply` option set to `True`, a reply object is stored for five (5) minutes OR until the reply is sent, and contains the following data:
| Reply Object           |
|------------------------|
| Userproxy ID           |
| Channel ID             |
| Queued Message Content |
| Queued Attachment URL  |

When a message is proxied in a server that has the `logclean` option enabled, the following data is stored for one (1) minute:
| Logclean Object        |
|------------------------|
| Hashed Message Content |
| User ID                |
| Channel ID             |
| User Name              |

When using the userproxy `reply` command, a userproxy reply object is stored for fifteen (15) minutes OR until the reply is sent, and contains the following data:
| Userproxy Reply Object       |
|------------------------------|
| Reply Message ID             |
| Referenced Message Content   |
| Referenced Message Author ID |

### 4.1 Data Caching
Data caching is used to improve performance and reduce the number of API requests made to Discord. Cached data is stored for one (1) day from the last update of the given data.

Messages have their content and attachments removed before being cached.

## 5. Use of Data
All data collected is strictly necessary for the functionality of /plu/ral:
- Group, member, and config objects are user-provided and required for core bot functionality
- Message logs are required for message editing, proxy information commands, and message API functionality

## 6. Data Storage and Security
Data is stored in the United States, outside of the EU/EEA. Security measures include:
- Double encryption at rest (database-level and disk encryption)
- Encryption in transit (TLS/SSL)
- Secure access limited to developers

## 7. Your Rights
Users have the following rights regarding their data:
- Right to access: Use `/export format:full` to receive all your stored data
- Right to correction: Use relevant bot commands to update your stored data
- Right to data portability: Use `/export` command with desired format
- Right to erasure: Use `/delete_all_data` command

Due to the bot's operational requirements, data processing cannot be restricted or objected to while using the bot, as all processed data is essential for functionality. Users who wish to stop data processing should cease using the bot.

## 8. Data Breach Notification
In the event of a data breach, users will be notified within 48 hours via the announcements channel on the [support server](https://discord.gg/4mteVXBDW7).

## 9. Changes to the Privacy Policy
This privacy policy may be updated at any time. If the changes decrease user privacy in any way, users will be notified via the [support server](https://discord.gg/4mteVXBDW7).

## 10. Open Source
/plu/ral is open source under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).

The source code is available on [GitHub](https://github.com/tyrantlink/plural) for anyone to review.

## 11. Data Sharing
/plu/ral does not share data with any third parties, except as required by law.
