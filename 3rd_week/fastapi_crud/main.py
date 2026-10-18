from fastapi import FastAPI

import models
from database import engine
from routers import items

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Products CRUD API", version="1.0.0")

app.include_router(items.router)


@app.get("/")
def root():
    return {"message": "Products CRUD API is running. Visit /docs for Swagger UI."}
