use mongo_document::Document;
use mongodb::bson::oid::ObjectId;
use serde::{Deserialize, Serialize};

use crate::db::enums::ApplicationScope;

#[derive(Debug, Document, Serialize, Deserialize)]
#[document(collection = "applications")]
pub struct Application {
    #[serde(rename = "_id")]
    pub id: ObjectId,
    pub name: String,
    pub description: String,
    pub icon: Option<String>,
    pub developer: u64,
    pub token: String,
    pub scope: ApplicationScope,
    pub endpoint: String,
    pub authorized_count: u32
}

impl Application {
    pub fn empty() -> Self {
        Self {
            id: ObjectId::new(),
            name: String::new(),
            description: String::new(),
            icon: None,
            developer: 0,
            token: String::new(),
            scope: ApplicationScope::None,
            endpoint: String::new(),
            authorized_count: 0
        }
    }
}
