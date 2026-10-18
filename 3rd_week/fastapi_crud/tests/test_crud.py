import models
import schemas
from crud import (
    create_product,
    delete_product,
    get_product,
    get_products,
    update_product,
)


def _create(db, name="Test", price=10.0, is_available=True):
    return create_product(
        db, schemas.ProductCreate(name=name, price=price, is_available=is_available)
    )


def test_create_product(db_session):
    product = _create(db_session, name="CRUD Create", price=15.5)
    assert product.id is not None
    assert product.name == "CRUD Create"
    assert product.price == 15.5
    assert product.is_available is True


def test_get_product(db_session):
    created = _create(db_session)
    fetched = get_product(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == created.name


def test_get_product_not_found(db_session):
    assert get_product(db_session, 999) is None


def test_get_products(db_session):
    _create(db_session, name="A")
    _create(db_session, name="B")
    _create(db_session, name="C")

    products = get_products(db_session)
    assert len(products) == 3


def test_get_products_skip_limit(db_session):
    for i in range(5):
        _create(db_session, name=f"P{i}")

    products = get_products(db_session, skip=1, limit=2)
    assert len(products) == 2
    assert products[0].name == "P1"


def test_update_product(db_session):
    created = _create(db_session, name="Old", price=1.0)
    updated = update_product(
        db_session,
        created.id,
        schemas.ProductUpdate(name="New", price=99.0, is_available=False),
    )
    assert updated is not None
    assert updated.name == "New"
    assert updated.price == 99.0
    assert updated.is_available is False


def test_update_product_not_found(db_session):
    result = update_product(
        db_session,
        999,
        schemas.ProductUpdate(name="New", price=99.0, is_available=False),
    )
    assert result is None


def test_delete_product(db_session):
    created = _create(db_session)
    deleted = delete_product(db_session, created.id)
    assert deleted is not None
    assert deleted.id == created.id
    assert get_product(db_session, created.id) is None


def test_delete_product_not_found(db_session):
    assert delete_product(db_session, 999) is None


def test_product_model_tablename():
    assert models.Product.__tablename__ == "products"
