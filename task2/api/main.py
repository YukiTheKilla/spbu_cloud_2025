from fastapi import FastAPI
import httpx

app = FastAPI()
DB_URL = "http://db:8000/users"

@app.get("/get_users")
def get_users(limit: int = 10):
    resp = httpx.get(DB_URL, params={"limit": limit})
    return resp.json()

#http://localhost:8001/get_users?limit=5