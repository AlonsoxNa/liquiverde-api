class InvalidBarcodeError(ValueError):
    pass


def normalize_barcode(value: str) -> str:
    barcode = value.strip()
    if not barcode.isascii() or not barcode.isdigit():
        raise InvalidBarcodeError("El código debe contener únicamente dígitos.")
    if len(barcode) not in {8, 12, 13}:
        raise InvalidBarcodeError("El código debe tener 8, 12 o 13 dígitos.")
    if set(barcode) == {"0"}:
        raise InvalidBarcodeError("El código no puede estar formado solo por ceros.")
    if not has_valid_checksum(barcode):
        raise InvalidBarcodeError("El dígito verificador no es válido.")
    return f"0{barcode}" if len(barcode) == 12 else barcode


def has_valid_checksum(barcode: str) -> bool:
    body = barcode[:-1]
    expected_check_digit = int(barcode[-1])
    weighted_sum = sum(
        int(digit) * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(body))
    )
    calculated_check_digit = (10 - weighted_sum % 10) % 10
    return calculated_check_digit == expected_check_digit
