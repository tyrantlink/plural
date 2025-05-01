use std::collections::{HashMap, HashSet};

use mongo_document::Document;
use mongodb::bson::oid::ObjectId;
use serde::{Deserialize, Serialize};

use super::enums::{
    ApplicationScope,
    PaginationStyle,
    ReplyFormat,
    SupporterTier
};

#[derive(Debug, Document, Serialize, Deserialize)]
#[document(collection = "usergroups")]
pub struct Usergroup {
    #[serde(rename = "_id")]
    pub id: ObjectId,
    pub users: HashSet<u64>,
    pub config: UsergroupConfig,
    pub userproxy_config: UserproxyConfig,
    pub data: UsergroupData
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UsergroupConfig {
    pub account_tag: String,
    pub reply_format: ReplyFormat,
    pub ping_replies: bool,
    pub groups_in_autocomplete: bool,
    pub pagination_style: PaginationStyle,
    pub roll_embed: bool,
    pub tag_format: String,
    pub pronoun_format: String,
    pub include_tag: bool,
    pub include_pronouns: bool,
    pub display_name_order: [String; 3],
    pub private_member_info: bool
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UserproxyConfig {
    pub reply_format: ReplyFormat,
    pub dm_reply_format: ReplyFormat,
    pub ping_replies: bool,
    pub include_tag: bool,
    pub include_pronouns: bool,
    pub attachment_count: u32,
    pub self_hosted: bool,
    pub required_message_parameter: bool,
    pub name_in_reply_command: bool,
    pub include_attribution: bool
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UsergroupData {
    pub selfhosting_token: Option<String>,
    pub userproxy_version: Option<String>,
    pub supporter_tier: SupporterTier,
    pub applications: HashMap<String, ApplicationScope>,
    pub image_limit: u32,
    pub sp_token: Option<String>,
    pub sp_id: Option<String>
}
