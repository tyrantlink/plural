pub const TOKEN_EPOCH: u64 = 1727988244890;
pub const BASE66CHARS: &str =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=-_~";

// ? why am i stubborn

pub fn encode_b66(bytes: &[u8]) -> String {
    if bytes.is_empty() || bytes.iter().all(|&b| b == 0) {
        return BASE66CHARS.chars().next().unwrap().to_string();
    }

    let mut b66 = String::new();

    let mut current_bytes = bytes.to_vec();

    while !current_bytes.iter().all(|&b| b == 0) {
        let mut remainder = 0;

        let mut new_bytes: Vec<u8> = Vec::new();

        let mut leading_zeros = true;

        for byte in current_bytes.iter() {
            let intermediate = (remainder * 256) + (*byte as u32);

            let quotient = intermediate / 66;

            remainder = intermediate % 66;

            if quotient != 0 || !leading_zeros {
                new_bytes.push(quotient as u8);

                leading_zeros = false;
            }
        }

        if new_bytes.is_empty() {
            new_bytes.push(0);
        }

        b66.insert(0, BASE66CHARS.chars().nth(remainder as usize).unwrap());

        current_bytes = new_bytes;
    }

    b66
}

pub fn decode_b66(b66: &str) -> Vec<u8> {
    let mut current_value: Vec<u8> = vec![0];

    for c in b66.chars() {
        let char_value = BASE66CHARS.find(c).unwrap() as u32;

        let mut carry = 0;

        for byte in current_value.iter_mut().rev() {
            let intermediate = (*byte as u32) * 66 + carry;

            *byte = (intermediate % 256) as u8;

            carry = intermediate / 256;
        }

        while carry > 0 {
            current_value.insert(0, (carry % 256) as u8);

            carry /= 256;
        }

        let mut carry = char_value;

        for byte in current_value.iter_mut().rev() {
            let intermediate = (*byte as u32) + carry;

            *byte = (intermediate % 256) as u8;

            carry = intermediate / 256;
        }

        while carry > 0 {
            current_value.insert(0, (carry % 256) as u8);

            carry /= 256;
        }
    }

    let mut first_nonzero = 0;

    while first_nonzero < current_value.len() - 1 &&
        current_value[first_nonzero] == 0
    {
        first_nonzero += 1;
    }

    current_value[first_nonzero..].to_vec()
}
