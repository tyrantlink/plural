use mongo_document::Document;
use mongodb::bson::oid::ObjectId;
use serde::{Deserialize, Serialize};

#[derive(Debug, Document, Serialize, Deserialize)]
#[document(collection = "guilds")]
pub struct Guild {
    #[serde(rename = "_id")]
    pub id:     ObjectId,
    pub config: GuildConfig
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildConfig {
    pub logclean:          bool,
    pub force_include_tag: bool,
    pub log_channel:       Option<u64>
}
