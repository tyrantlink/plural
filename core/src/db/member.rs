use std::collections::HashSet;

use bson::oid::ObjectId;
use mongo_document::Document;
use serde::{Deserialize, Serialize};

#[derive(Debug, Document, Serialize, Deserialize)]
#[document(collection = "members")]
pub struct Member {
    #[serde(rename = "_id")]
    pub id: ObjectId,
    pub name: String,
    pub custom_id: String,
    pub pronouns: String,
    pub bio: String,
    pub birthday: String,
    pub color: Option<i32>,
    pub avatar: Option<String>,
    pub proxy_tags: Vec<ProxyTag>,
    pub userproxy: Option<Userproxy>,
    pub simplyplural_id: Option<String>
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ProxyTag {
    pub id: ObjectId,
    pub prefix: String,
    pub suffix: String,
    pub regex: bool,
    pub case_sensitive: bool,
    pub avatar: Option<String>
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Userproxy {
    pub bot_id:     u64,
    pub public_key: String,
    pub token:      String,
    pub command:    String,
    pub guilds:     HashSet<u64>
}

// impl Member {
//     pub fn expired(&self) -> bool {
//         (
//             self.ts.to_chrono() +
//             chrono::Duration::minutes(14) +
//             chrono::Duration::seconds(30)
//         ) < chrono::Utc::now()
//     }
// }
