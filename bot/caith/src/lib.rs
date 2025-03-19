use caith::{Roller, RollResultType};
use pyo3::prelude::*;

#[pyfunction]
fn roll(input: &str) -> PyResult<(String, String)> {
    let result = Roller::new(input)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
        .roll()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    match result.get_result() {
        RollResultType::Single(result) => {Ok((
            result.get_history().iter().map(|roll| {
                roll.to_string()
            }).collect::<Vec<String>>().join(""),
            result.get_total().to_string()
        ))}
        _ => {
            Ok((String::from("Error"), String::new()))
        }
    }
}


#[pymodule(name = "caith")]
fn caith_(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(roll, m)?)?;
    Ok(())
}
