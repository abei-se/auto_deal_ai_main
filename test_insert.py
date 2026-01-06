from db import insert_car

test_car = {
    "platform": "willhaben",
    "external_id": "TEST123",
    "title": "Audi A4 2.0 TDI Test",
    "brand": "Audi",
    "model": "A4",
    "year": 2019,
    "km": 120000,
    "price": 18900,
    "location": "Wien",
    "url": "https://www.willhaben.at/test-inserat"
}

insert_car(test_car)
print("✅ Test-Auto gespeichert")
