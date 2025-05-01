use proc_macro::TokenStream;
use quote::quote;
use syn::{DeriveInput, parse_macro_input};

#[proc_macro_derive(Document, attributes(document))]
pub fn document_derive(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);

    let name = &input.ident;

    // ? i stole this part from the internet
    let collection_name = input
        .attrs
        .iter()
        .find(|attr| attr.path.is_ident("document"))
        .and_then(|attr| attr.parse_meta().ok())
        .and_then(|meta| {
            if let syn::Meta::List(meta_list) = meta {
                meta_list.nested.into_iter().find_map(|nested_meta| {
                        let syn::NestedMeta::Meta(syn::Meta::NameValue(
                            name_value
                        )) = nested_meta
                        else {
                            return None;
                        };

                        if !name_value.path.is_ident("collection") {
                            return None;
                        };

                        let syn::Lit::Str(lit_str) = name_value.lit else {
                            return None;
                        };

                        Some(lit_str.value())
                    })
            } else {
                None
            }
        });

    let collection_name = match collection_name {
        Some(name) => name,
        None => {
            return TokenStream::from(quote! {compile_error!(
                    "The #[derive(Document)] macro requires a \
                    #[document(collection = \"...\")] attribute."
            )});
        }
    };

    TokenStream::from(quote! {
        impl #name {
            pub async fn find_one(
                query: mongodb::bson::Document
            ) -> Result<Option<#name>, mongodb::error::Error>
            where #name: serde::de::DeserializeOwned {
                let collection = crate::mongo()
                    .collection::<#name>(#collection_name);

                let find = collection.find_one(query);

                // ! add other options (projection, sort, etc.)
                // ! since you can't use the builder in the macro

                find.await
            }

            pub async fn count_documents(
                query: mongodb::bson::Document
            ) -> Result<u64, mongodb::error::Error> {
                crate::mongo()
                    .collection::<#name>(#collection_name)
                    .count_documents(query)
                    .await
            }
        }
    })
}
