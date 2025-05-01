use std::{collections::HashMap, sync::OnceLock};

use opentelemetry::{
    KeyValue,
    global,
    trace::{Span, Status, Tracer}
};
pub use reqwest::Method;
use reqwest::header::{ACCEPT, ACCEPT_ENCODING, AUTHORIZATION};
use serde::de::DeserializeOwned;


static CLIENT: OnceLock<reqwest::Client> = OnceLock::new();


pub struct Request {
    method:  Method,
    url:     String,
    token:   Option<String>,
    trace:   bool,
    headers: HashMap<String, String>
}


impl Request {
    pub fn new(method: Method, url: &str) -> Self {
        Self {
            method,
            url: url.to_string(),
            token: None,
            trace: true,
            headers: HashMap::new()
        }
    }

    pub fn with_token(mut self, token: &str) -> Self {
        self.token = Some(token.to_string());
        self
    }

    pub fn suppress_tracer(mut self) -> Self {
        self.trace = false;
        self
    }

    pub fn with_header(mut self, key: &str, value: &str) -> Self {
        self.headers.insert(key.to_string(), value.to_string());
        self
    }

    pub fn get_client() -> &'static reqwest::Client {
        CLIENT.get_or_init(|| {
            reqwest::Client::builder()
                .user_agent("Plural/4.0a")
                .default_headers(reqwest::header::HeaderMap::from_iter([
                    (ACCEPT_ENCODING, "gzip".parse().unwrap()),
                    (ACCEPT, "application/json".parse().unwrap())
                ]))
                .build()
                .unwrap()
        })
    }

    pub async fn send<T>(
        self
    ) -> Result<Option<T>, Box<dyn std::error::Error>>
    where T: DeserializeOwned {
        let client = Request::get_client();

        let mut request = client.request(self.method.clone(), self.url.clone());

        if let Some(token) = self.token {
            request = request.header(AUTHORIZATION, format!("Bot {token}"));
        }

        for (key, value) in self.headers {
            request = request.header(key, value);
        }

        let operation = async move {
            let response = request.send().await?;

            match response.status().as_u16() {
                200 => {
                    Ok(Some(response.json::<T>().await.map_err(|e| {
                        Box::new(e) as Box<dyn std::error::Error>
                    })?))
                }
                204 => Ok(None),
                _ => Err(format!(
                    "Request failed with status code {}",
                    response.status()
                )
                .into())
            }
        };

        if self.trace {
            let tracer = global::tracer("");
            let mut span = tracer
                .span_builder(format!(
                    "{} /{}",
                    self.method,
                    self.url.splitn(6, '/').last().unwrap_or_default()
                ))
                .with_attributes([
                    KeyValue::new("http.method", self.method.to_string()),
                    KeyValue::new(
                        "http.path",
                        format!(
                            "/{}",
                            self.url.splitn(4, '/').last().unwrap_or_default()
                        )
                    )
                ])
                .start(&tracer);

            let result: Result<Option<T>, Box<dyn std::error::Error>> =
                operation.await;

            match &result {
                Ok(_) => {
                    span.set_status(Status::Ok);
                }
                Err(e) => {
                    span.set_status(Status::Error {
                        description: e.to_string().into()
                    });
                    span.record_error(e.as_ref());
                }
            }

            Ok(result?)
        } else {
            Ok(operation.await?)
        }
    }
}
