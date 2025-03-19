use caith::{Roller, RollResultType, RollHistory};
use rand::{thread_rng, seq::SliceRandom};
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
                match roll {
                    RollHistory::Roll(rolls) => {
                        let mut values = rolls.iter().map(|roll| {
                            roll.res
                        }).collect::<Vec<u64>>();

                        values.shuffle(&mut thread_rng());

                        format!("[{}]", values.iter().map(|r| {
                            r.to_string()
                        }).collect::<Vec<String>>().join(", "))}
                    _ => roll.to_string()}
            }).collect::<Vec<String>>().join(""),
            result.get_total().to_string()
        ))}
        _ => {
            Err(pyo3::exceptions::PyValueError::new_err(
                "Only single rolls are supported",
            ))
        }
    }
}


#[pymodule(name = "caith")]
fn caith_(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(roll, m)?)?;
    Ok(())
}
