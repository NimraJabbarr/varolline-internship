from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import crud
import schemas
from database import get_db

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
def create_item(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db=db, product=product)


@router.get("/", response_model=list[schemas.ProductResponse])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_products(db=db, skip=skip, limit=limit)


@router.get("/{item_id}", response_model=schemas.ProductResponse)
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db=db, product_id=item_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.put("/{item_id}", response_model=schemas.ProductResponse)
def update_item(item_id: int, product: schemas.ProductUpdate, db: Session = Depends(get_db)):
    db_product = crud.update_product(db=db, product_id=item_id, product=product)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_product = crud.delete_product(db=db, product_id=item_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": f"Product {item_id} deleted successfully"}
