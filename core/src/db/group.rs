use std::collections::{HashMap, HashSet};

use mongo_document::Document;
use mongodb::bson::oid::ObjectId;
use serde::{Deserialize, Serialize};

use crate::db::enums::GroupSharePermissionLevel;

#[derive(Debug, Document, Serialize, Deserialize)]
#[document(collection = "groups")]
pub struct Group {
    #[serde(rename = "_id")]
    pub id:       ObjectId,
    pub name:     String,
    pub account:  ObjectId,
    pub users:    HashMap<String, GroupSharePermissionLevel>,
    pub avatar:   Option<String>,
    pub channels: HashSet<u64>,
    pub tag:      Option<String>,
    pub members:  HashSet<ObjectId>
}
