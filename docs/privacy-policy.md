# Privacy Policy
Effective: 13 December 2024

## 1. Perpetual Data Collection
/plu/ral stores all data explicitly provided via interactions, including but not limited to:
- Group data
- Member data
- Config settings

## 2. Changes to the Privacy Policy
This privacy policy may be updated at any time. If the changes decrease user privacy in any way, users will be notified via the [support server](https://discord.gg/4mteVXBDW7).

## 3. Temporary Data Collection
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

### 3.1 Data Caching
Data caching is used to improve performance and reduce the number of API requests made to Discord. Cached data is stored for one (1) day from the last update of the given data.

Messages have their content and attachments removed before being cached.

## 4. Use of Data
Data collected is used strictly for the functionality of /plu/ral.

## 5. Open Source
/plu/ral is open source under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).

The source code is available on [GitHub](https://github.com/tyrantlink/plural) for anyone to review.

## 6. Data Sharing
/plu/ral does not share data with any third parties, except as required by law.

## 7. Data Deletion
Users may request data deletion by running the `/delete_all_data` command.

## 8. Data Storage
Data is stored securely behind multiple layers of encryption and only accessible by the developers of /plu/ral.