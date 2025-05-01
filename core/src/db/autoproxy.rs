use mongo_document::Document;
use mongodb::bson::{DateTime, oid::ObjectId};
use serde::{Deserialize, Serialize};

use super::enums::AutoproxyMode;

#[derive(Debug, Document, Serialize, Deserialize)]
#[document(collection = "autoproxy")]
pub struct Autoproxy {
    #[serde(rename = "_id")]
    pub id:     ObjectId,
    pub user:   ObjectId,
    pub guild:  Option<u64>,
    pub mode:   AutoproxyMode,
    pub member: Option<ObjectId>,
    pub ts:     Option<DateTime>
}
