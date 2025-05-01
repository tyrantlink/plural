use bson::{DateTime, oid::ObjectId};
use mongo_document::Document;
use serde::{Deserialize, Serialize};

#[derive(Debug, Document, Serialize, Deserialize)]
#[document(collection = "messages")]
pub struct Message {
    #[serde(rename = "_id")]
    pub id: ObjectId,
    pub original_id: Option<u64>,
    pub proxy_id: u64,
    pub author_id: u64,
    pub user: ObjectId,
    pub channel_id: u64,
    pub member_id: ObjectId,
    pub reason: String,
    pub webhook_id: Option<u64>,
    pub reference_id: Option<u64>,
    pub bot_id: Option<u64>,
    pub interaction_token: Option<String>,
    pub ts: DateTime
}

impl Message {
    pub fn expired(&self) -> bool {
        (self.ts.to_chrono() +
            chrono::Duration::minutes(14) +
            chrono::Duration::seconds(30)) <
            chrono::Utc::now()
    }
}
