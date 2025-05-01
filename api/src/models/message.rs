use bson::doc;
use plural_core::db::{Member, Message, MongoError};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct MessageModel {
    original_id:  Option<String>,
    proxy_id:     String,
    author_id:    String,
    channel_id:   String,
    member_id:    String,
    reason:       String,
    webhook_id:   Option<String>,
    reference_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    // nest option so we can differentiate between
    // a member that was not found and
    // a response without the ?member=true param
    member: Option<Option<MemberAuthorModel>>
}

#[derive(Serialize, Deserialize)]
pub struct MemberAuthorModel {
    id:         String,
    name:       String,
    pronouns:   String,
    bio:        String,
    birthday:   String,
    color:      Option<i32>,
    avatar_url: Option<String>,
    supporter:  bool,
    private:    bool
}

impl MessageModel {
    pub async fn from_message(
        message: Message,
        with_member: bool
    ) -> Result<Self, MongoError> {
        Ok(Self {
            original_id:  message.original_id.map(|id| id.to_string()),
            proxy_id:     message.proxy_id.to_string(),
            author_id:    message.author_id.to_string(),
            channel_id:   message.channel_id.to_string(),
            member_id:    message.member_id.to_hex(),
            reason:       message.reason,
            webhook_id:   message.webhook_id.map(|id| id.to_string()),
            reference_id: message.reference_id.map(|id| id.to_string()),
            member:       if with_member {
                if let Some(member) = Member::find_one(doc! {
                    "_id": message.member_id
                })
                .await?
                {
                    Some(Some(MemberAuthorModel::from_member(member)))
                } else {
                    Some(None)
                }
            } else {
                None
            }
        })
    }
}

impl MemberAuthorModel {
    pub fn from_member(member: Member) -> Self {
        Self {
            id:         member.id.to_hex(),
            name:       member.name,
            pronouns:   member.pronouns,
            bio:        member.bio,
            birthday:   member.birthday,
            color:      member.color,
            avatar_url: member.avatar,
            supporter:  false,
            private:    false
        }
    }
}
