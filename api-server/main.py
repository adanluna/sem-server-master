from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "API forense activa"}
