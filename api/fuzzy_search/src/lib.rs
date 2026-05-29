use std::cmp::Ordering::Equal;

use pyo3::prelude::*;
use strsim::jaro_winkler;

#[pyfunction]
fn search(query: &str, choices: Vec<(String, String)>) -> Vec<(String, String)> {
    let query = query.to_lowercase();

    if query.is_empty() {
        return choices;
    }

    let mut scored = choices
        .into_iter()
        .map(|(name, value)| {
            let choice_name = name.to_lowercase();

            (
                name,
                value,
                if choice_name.starts_with(&query) {
                    1.0
                } else if choice_name.contains(&query) {
                    0.8 + (query.len() as f64 / choice_name.len() as f64)
                } else {
                    jaro_winkler(&query, &choice_name)
                },
            )
        })
        .filter(|(_, _, score)| *score > 0.6)
        .collect::<Vec<_>>();

    scored.sort_by(|(_, _, a), (_, _, b)| b.partial_cmp(a).unwrap_or(Equal));

    scored
        .into_iter()
        .map(|(name, value, _)| (name, value))
        .collect()
}

#[pymodule]
fn fuzzy_search(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(search, m)?)?;
    Ok(())
}
