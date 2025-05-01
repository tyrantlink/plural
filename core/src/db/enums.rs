use bitflags::bitflags;
use serde::{
    Deserialize,
    Deserializer,
    Serialize,
    Serializer,
    de::Error as DeError
};
use serde_repr::{Deserialize_repr, Serialize_repr};

bitflags! {
    #[derive(Debug, PartialEq)]
    pub struct ApplicationScope: u32 {
        const None = 0;
        const UserEvents = 1 << 0;
        const UserWrite = 1 << 1;
        const SendMessages = 1 << 2;
        const UserproxyTokens = 1 << 3;
        const SimplyPluralTokens = 1 << 4;
    }
}

impl Serialize for ApplicationScope {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where S: Serializer {
        serializer.serialize_u32(self.bits())
    }
}

impl<'de> Deserialize<'de> for ApplicationScope {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where D: Deserializer<'de> {
        let bits = u32::deserialize(deserializer)?;

        ApplicationScope::from_bits(bits).ok_or_else(|| {
            D::Error::custom(format!("Invalid ApplicationScope bits: {bits}"))
        })
    }
}

impl ApplicationScope {
    pub fn pretty_name(self) -> &'static str {
        match self {
            ApplicationScope::UserEvents => "User Events",
            ApplicationScope::UserWrite => "User Write",
            ApplicationScope::SendMessages => "Send Messages",
            ApplicationScope::UserproxyTokens => "Userproxy Tokens",
            ApplicationScope::SimplyPluralTokens => "SimplyPlural Tokens",
            _ => "None"
        }
    }

    pub fn description(self) -> &'static str {
        match self {
            ApplicationScope::UserEvents => "Receive user update events",
            ApplicationScope::UserWrite => "Modify user data",
            ApplicationScope::SendMessages => "Access to send messages",
            ApplicationScope::UserproxyTokens => {
                "Userproxy tokens will be included in user data"
            }
            ApplicationScope::SimplyPluralTokens => {
                "SimplyPlural tokens will be included in user data"
            }
            _ => "None"
        }
    }

    pub fn approval_required(self) -> bool {
        matches!(
            self,
            ApplicationScope::SendMessages |
                ApplicationScope::UserproxyTokens |
                ApplicationScope::SimplyPluralTokens
        )
    }
}

#[derive(Debug, Serialize_repr, Deserialize_repr)]
#[repr(u8)]
pub enum AutoproxyMode {
    LATCH    = 0,
    FRONT    = 1,
    LOCKED   = 2,
    DISABLED = 3
}

impl AutoproxyMode {
    pub fn description(self) -> &'static str {
        match self {
            AutoproxyMode::LATCH => {
                "Using proxy tags will switch the autoproxied member"
            }
            AutoproxyMode::FRONT => {
                "Using proxy tags will not modify the autoproxied member"
            }
            AutoproxyMode::LOCKED => {
                "Proxy tags will be ignored and the autoproxied member will \
                 always be used"
            }
            AutoproxyMode::DISABLED => {
                "All proxying is disabled (including with proxy tags)"
            }
        }
    }
}

#[derive(Debug, Serialize_repr, Deserialize_repr)]
#[repr(u8)]
pub enum GroupSharePermissionLevel {
    ProxyOnly  = 0,
    FullAccess = 1
}

#[derive(Debug, Serialize_repr, Deserialize_repr)]
#[repr(u8)]
pub enum PaginationStyle {
    BasicArrows = 0,
    TextArrows = 1,
    RemAndRam  = 2
}

#[derive(Debug, Serialize_repr, Deserialize_repr)]
#[repr(u8)]
pub enum ReplyFormat {
    None   = 0,
    Inline = 1,
    Embed  = 2
}

#[derive(Debug, Serialize_repr, Deserialize_repr)]
#[repr(u8)]
pub enum ReplyType {
    Queue = 0,
    Reply = 1
}

#[derive(Debug, Serialize_repr, Deserialize_repr)]
#[repr(u8)]
pub enum ShareType {
    Usergroup = 0,
    Group     = 1
}

#[derive(Debug, Serialize_repr, Deserialize_repr)]
#[repr(u8)]
pub enum SupporterTier {
    None      = 0,
    Developer = 1,
    Supporter = 2,
    EarlySupporter = 3,
    ActiveSupporter = 4
}
