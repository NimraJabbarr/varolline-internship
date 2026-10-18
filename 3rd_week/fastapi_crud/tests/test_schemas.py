import pytest
from pydantic import ValidationError

from schemas import ProductCreate, ProductResponse, ProductUpdate


def test_product_create_valid():
    product = ProductCreate(name="Test", price=10.0)
    assert product.name == "Test"
    assert product.price == 10.0
    assert product.is_available is True


def test_product_create_zero_price():
    with pytest.raises(ValidationError):
        ProductCreate(name="Test", price=0)


def test_product_create_negative_price():
    with pytest.raises(ValidationError):
        ProductCreate(name="Test", price=-1)


def test_product_create_empty_name():
    with pytest.raises(ValidationError):
        ProductCreate(name="", price=10)


def test_product_create_name_too_long():
    with pytest.raises(ValidationError):
        ProductCreate(name="x" * 101, price=10)


def test_product_update_schema():
    product = ProductUpdate(name="Updated", price=20.0, is_available=False)
    assert product.name == "Updated"
    assert product.is_available is False


def test_product_response_from_orm(db_session):
    import models

    db_product = models.Product(name="ORM", price=5.0, is_available=True)
    db_session.add(db_product)
    db_session.commit()
    db_session.refresh(db_product)

    response = ProductResponse.model_validate(db_product)
    assert response.id == db_product.id
    assert response.name == "ORM"
